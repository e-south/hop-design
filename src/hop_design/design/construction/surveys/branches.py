"""Address compensation requests without materializing a giant product roster."""

import json
from collections import OrderedDict
from dataclasses import dataclass
from functools import cached_property
from math import prod
from typing import Any

from hop_design.models.construction.complete.accounting import (
    CompositionEnumerationPolicy,
    CompositionPruningMode,
)
from hop_design.models.construction.complete.composition_domain import source_context_count
from hop_design.models.construction.complete.source_preparation.policy import primer_required_length
from hop_design.models.construction.discovery.placement import EndPlacement
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.construction.product_request import (
    ProductBasalReleaseProjection,
    ProductRequest,
)
from hop_design.models.construction.scaffold import constrain_foldback_geometry
from hop_design.models.construction.search import SearchScope, SearchStopMode
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.construction.targets import FoldbackTarget, NickStrandSelection
from hop_design.models.enzymes import (
    EnzymeClass,
    EnzymePermissions,
    EnzymeProvisioningPolicy,
    EnzymeRole,
)
from hop_design.models.physical import Strand
from hop_design.serialization import canonical_json_bytes

from ..overhead import iter_foldback_geometries
from .contexts import source_context_at
from .coordinates import coordinate_at
from .geometry_order import GeometryOrder, foldback_costs, placement_costs

_PRODUCT_CACHE_ENTRIES = 16
_PRODUCT_CACHE_BYTES = 2 * 1024 * 1024


def _policy(
    request: InterfaceSurveyRequest, permissions: EnzymePermissions
) -> EnzymeProvisioningPolicy:
    return EnzymeProvisioningPolicy.model_validate_json(
        json.dumps(
            {
                **permissions.model_dump(mode="json"),
                "catalog": request.enzyme_catalog.model_dump(mode="json", by_alias=True),
            }
        )
    )


def _release_permission(permissions: EnzymePermissions, method: str) -> dict[str, Any]:
    """Restrict an already permitted role; never add to caller permissions."""
    data = permissions.model_dump()
    data["role_restrictions"] = (
        *(role for role in data["role_restrictions"] if role["role"] != "end_generation"),
        {"role": EnzymeRole.END_GENERATION, "allowed_enzyme_ids": (method,)},
    )
    return data


@dataclass(frozen=True)
class SurveyBranches:
    """Stable geometry/method/context addresses; local sequence constraints stay joint."""

    request: InterfaceSurveyRequest

    @cached_property
    def _products(
        self,
    ) -> OrderedDict[tuple[int, int, SurveyEvaluationLimits], tuple[ProductRequest, int]]:
        # Invocation-owned: the survey request is fixed on this branch translator.
        return OrderedDict()

    @cached_property
    def _catalog_member_bytes(self) -> int:
        member = {
            "enzyme_catalog": self.request.enzyme_catalog.model_dump(mode="json", by_alias=True)
        }
        # The product already has braces and a final newline. Replace those
        # three bytes of this one-member object with its separating comma.
        return len(canonical_json_bytes(member)) - 2

    @cached_property
    def placements(self) -> tuple[EndPlacement, ...]:
        """Prefer less added DNA while reaching changes on either side early.

        Only declared pairs participate; this does not invent cross-combinations
        when the caller permits a non-Cartesian roster.
        """
        return tuple(
            sorted(
                self.request.placements,
                key=lambda p: (p.left_bp + p.right_bp, p.left_bp, p.right_bp),
            )
        )

    @cached_property
    def foldback_cases(self) -> tuple[FoldbackTarget, ...]:
        cases = tuple(
            target.model_copy(update={"nick_strand": strand})
            for target in iter_foldback_geometries(
                constrain_foldback_geometry(
                    self.request.foldback.geometry,
                    maximum=self.request.foldback.max_retained_overhead_nt,
                    requirements=self.request.whole_route_constraints.hairpin_scaffold,
                ),
                maximum=self.request.foldback.max_retained_overhead_nt,
            )
            for strand in (
                tuple(Strand)
                if target.nick_strand is NickStrandSelection.ANY
                else (target.nick_strand,)
            )
        )
        required = primer_required_length(
            self.request.materialization.source_preparation.reverse_primer
        )
        # A non-authoritative ordering preference, never an exclusion. Exact
        # sequence/program replay remains responsible for the actual source span.
        return tuple(
            sorted(
                cases,
                key=lambda target: (
                    2 * target.annealing_arm_length_bp
                    + target.loop_length_nt
                    - target.junction_offset_nt
                    < required,
                ),
            )
        )

    @cached_property
    def release_methods(self) -> tuple[str, ...]:
        request = self.request
        basal = _policy(request, request.basal.enzymes)
        release = _policy(request, request.release.enzymes)
        return tuple(
            sorted(
                str(enzyme.enzyme_id)
                for enzyme in request.enzyme_catalog.enzymes
                if enzyme.enzyme_class is EnzymeClass.DUPLEX_RESTRICTION
                and basal.permits(enzyme.enzyme_id, role=EnzymeRole.END_GENERATION)
                and release.permits(enzyme.enzyme_id, role=EnzymeRole.END_GENERATION)
            )
        )

    @cached_property
    def geometry_sizes(self) -> tuple[int, ...]:
        request = self.request
        return (
            len(request.placements),
            len(request.basal.geometry.nick_offsets_nt),
            len(request.basal.annealing_lengths_nt),
            len(self.release_methods),
            len(self.foldback_cases),
            len(request.release.basal_projections),
        )

    @property
    def geometry_count(self) -> int:
        return prod(self.geometry_sizes)

    @cached_property
    def geometry_order(self) -> GeometryOrder:
        sizes = self.geometry_sizes
        return GeometryOrder(
            (
                placement_costs(self.placements),
                tuple(range(sizes[1])),
                tuple(range(sizes[2])),
                tuple(range(sizes[3])),
                foldback_costs(self.foldback_cases),
                tuple(range(sizes[5])),
            )
        )

    def search_order(self, limits: SurveyEvaluationLimits) -> GeometryOrder:
        """Execution objectives reorder cases, never their identities or permissions."""
        from .navigation.diversity import diversity_order

        if (
            limits.objective is not None
            and limits.objective.varies_local_methods
            and self.request.source_context_objective != "paired_scaffold_completions"
        ):
            raise ValueError(
                "Method-directed survey discovery requires paired_scaffold_completions; "
                "all_words retains its exhaustive visitation order."
            )
        return (
            self.geometry_order
            if limits.objective is None
            else diversity_order(self, limits.objective)
        )

    @cached_property
    def context_count(self) -> int:
        return source_context_count(self.request.materialization.source_preparation.source_ssdna)

    @property
    def count(self) -> int:
        return self.geometry_count * self.context_count

    def release_projection(self, branch: int) -> ProductBasalReleaseProjection:
        """Read the declared projection for an address, without evaluating a molecule."""
        if type(branch) is not int or not 0 <= branch < self.count:
            raise ValueError("Survey branch must lie within the declared compensation domain.")
        geometry = branch % self.geometry_count
        projection = coordinate_at(self.geometry_sizes, geometry)[-1]
        return self.request.release.basal_projections[projection]

    def product(
        self, target: int, *, branch: int, limits: SurveyEvaluationLimits
    ) -> ProductRequest:
        """Translate one declared branch through the existing product-intent contract."""
        request = self.request
        words = request.targets.pair_at(target)
        methods = self.release_methods
        count = self.count
        if type(branch) is not int or not 0 <= branch < count:
            raise ValueError("Survey branch must lie within the declared compensation domain.")
        cache_key = (target, branch, limits)
        if cache_key in self._products:
            self._products.move_to_end(cache_key)
            return self._products[cache_key][0]
        context_i, geometry_i = divmod(branch, self.geometry_count)
        placement_i, nick_i, association_i, method_i, foldback_i, _ = coordinate_at(
            self.geometry_sizes, geometry_i
        )
        placement = self.placements[placement_i]
        method = methods[method_i]
        foldback = self.foldback_cases[foldback_i]
        # This input was already admitted. Keep its immutable catalog instead of
        # serializing and reparsing every enzyme for every new grid address.
        # Python-mode values retain strict tuples/enums; all derived fields and
        # the complete ProductRequest still pass their ordinary validators.
        data = request.model_dump(
            by_alias=True, exclude={"preferred_preparation", "enzyme_catalog"}
        )
        data["enzyme_catalog"] = request.enzyme_catalog
        data.pop("source_context_objective", None)
        data.pop("preferred_source_contexts", None)
        data.pop("source_handle_seed", None)
        for key in ("targets", "interfaces", "placements"):
            del data[key]
        data.update(
            schema="hop.product-request/v1", endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX
        )
        data["ends"] = {
            side: {
                **getattr(request.interfaces, side).model_dump(),
                "cohesive_end_sequence": word,
                "payload_end_offset_bp": gap,
            }
            for side, word, gap in zip(
                ("left", "right"), words, (placement.left_bp, placement.right_bp), strict=True
            )
        }
        for family in ("foldback", "basal"):
            data[family]["search"] = {
                "max_retained_overhead_nt": data[family].pop("max_retained_overhead_nt"),
                "max_search_nodes": limits.local_nodes,
                "max_realizations": limits.local_realizations,
                "scope": SearchScope.ALL_REALIZATIONS,
                "stop": SearchStopMode.EXHAUSTIVE,
                "result_quota": None,
            }
        data["foldback"]["geometry"].update(
            annealing_arm_lengths_bp=(foldback.annealing_arm_length_bp,),
            junction_offsets_nt=(foldback.junction_offset_nt,),
            loop_lengths_nt=(foldback.loop_length_nt,),
            nick_strand=foldback.nick_strand,
        )
        if foldback.loop_sequence is not None:
            data["foldback"]["geometry"]["loop_sequences"] = (foldback.loop_sequence,)
        data["basal"].pop("annealing_lengths_nt")
        data["basal"]["geometry"].update(
            nick_offsets_nt=(request.basal.geometry.nick_offsets_nt[nick_i],),
            minimum_adapter_annealing_nt=request.basal.annealing_lengths_nt[association_i],
        )
        data["basal"]["enzymes"] = _release_permission(request.basal.enzymes, method)
        data["release"]["enzymes"] = _release_permission(request.release.enzymes, method)
        data["release"].pop("basal_projections")
        data["release"]["basal_projection"] = self.release_projection(branch)
        data["release"]["max_site_pairs"] = limits.release_site_pairs
        context = source_context_at(
            request.materialization.source_preparation.source_ssdna, context_i
        )
        if context is not None:
            data["materialization"]["source_preparation"]["source_ssdna"][
                "upstream_sequence_spec"
            ] = context
        data["enumeration"] = CompositionEnumerationPolicy(
            pruning=CompositionPruningMode.DISABLED, max_combinations=1, max_realizations=1
        )
        product = ProductRequest.model_validate(data)
        variable = product.model_dump(mode="json", by_alias=True, exclude={"enzyme_catalog"})
        size = len(canonical_json_bytes(variable)) + self._catalog_member_bytes
        if _PRODUCT_CACHE_ENTRIES > 0 and size <= _PRODUCT_CACHE_BYTES:
            self._products[cache_key] = product, size
            while (
                len(self._products) > _PRODUCT_CACHE_ENTRIES
                or sum(size for _, size in self._products.values()) > _PRODUCT_CACHE_BYTES
            ):
                self._products.popitem(last=False)
        return product
