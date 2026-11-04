"""Address local candidates through replayable, disjoint sequence-domain parts."""

from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass

from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain
from hop_design.kernel.construction.basal.programs import BasalPlacementFailure
from hop_design.kernel.construction.basal.sequence_index import BasalSequenceIndex
from hop_design.kernel.construction.foldback.domains import solve_foldback_sequence_domain
from hop_design.kernel.construction.foldback.solutions import FoldbackPlacementFailure
from hop_design.models.construction.complete.source_preparation.policy import SourceSsdnaPolicy
from hop_design.models.construction.product_pairing import ProductConstraintConflict
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.request import LocalNeighborhoodRequest
from hop_design.models.construction.search import FoldbackGeometryDomain
from hop_design.models.construction.sequence_sets import SequenceSpaceLimits
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..basal.traversal import iter_basal_work_units
from ..foldback.candidates import _payload_has_actionable_site
from ..foldback.traversal import iter_foldback_work_units
from ..overhead import foldback_overhead_levels
from .basal_population import BasalPopulation
from .basal_population import admit_population as admit_basal_population
from .branches import SurveyBranches
from .completion.frame_admission import BasalAdmissions
from .completion.interfaces import EndPairAdmission, EndPairRelations
from .completion.population import EndpointPopulation, condition_population
from .context_priority import ContextPriority, basal_context_hint
from .coordinates import coordinate_at, coordinate_rank
from .foldback_population import (
    FoldbackPopulation,
    admit_population,
    default_sequence_limits,
    population_request,
)
from .index import SurveyIndex

_POPULATION_CACHE_ENTRIES = 128
# Charge canonical result bytes; Python object overhead is additional.
_POPULATION_CACHE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class LocalExtent:
    """Largest canonical program stream, before reaction-stage admission."""

    parts: int
    work_units: int

    def partition(self, ordinal: int) -> dict[str, int]:
        if not 0 <= ordinal < self.parts:
            raise ValueError("Local part address lies outside its computed candidate extent.")
        return {"part_count": max(2, self.parts), "part_index": ordinal}


def local_extent(request: LocalNeighborhoodRequest) -> LocalExtent:
    """Count placement streams algebraically; never infer complete-route support."""
    largest, units = 0, 0
    if request.family.value == "foldback":
        assert isinstance(request.geometry_domain, FoldbackGeometryDomain)
        for level in foldback_overhead_levels(request.geometry_domain, request.search):
            for unit in iter_foldback_work_units(request, level=level):
                domain = solve_foldback_sequence_domain(
                    payload_sequence=unit.payload_sequence, target=unit.target, program=unit.program
                )
                count = (
                    1
                    if isinstance(domain, FoldbackPlacementFailure)
                    or _payload_has_actionable_site(unit)
                    else domain.precursor_cardinality
                )
                largest, units = max(largest, count), units + 1
    else:
        for overhead in range(request.search.max_retained_overhead_nt + 1):
            for basal_unit in iter_basal_work_units(request, retained_overhead_nt=overhead):
                basal_domain = solve_basal_sequence_domain(
                    payload_sequence=basal_unit.payload_sequence,
                    target=basal_unit.target,
                    endpoint=request.endpoint,
                    program=basal_unit.program,
                )
                count = (
                    1
                    if isinstance(basal_domain, BasalPlacementFailure)
                    else BasalSequenceIndex.create(basal_domain).cardinality
                )
                largest, units = max(largest, count), units + 1
    # Include empty parts too: aggregate coverage records every declared part,
    # rather than silently treating an algebraic cardinality as replay evidence.
    return LocalExtent(max(2, largest), units)


@dataclass(frozen=True)
class ProductParts:
    foldback: FoldbackPopulation | None = None
    basal: BasalPopulation | None = None
    conflict: ProductConstraintConflict | None = None
    endpoint: EndpointPopulation | None = None
    end_pair_admission: EndPairAdmission | None = None

    @property
    def basal_candidates(self) -> BasalPopulation | None:
        return self.basal if self.endpoint is None else self.endpoint.population

    @property
    def empty_endpoint(self) -> bool:
        return (self.endpoint is not None and self.endpoint.population.parts == 0) or (
            self.end_pair_admission is not None
            and not self.end_pair_admission.requested_pair_admitted
        )

    @property
    def empty_candidates(self) -> bool:
        return self.empty_local or self.empty_endpoint

    @property
    def count(self) -> int:
        if self.conflict is not None or self.empty_candidates:
            return 1
        assert self.foldback is not None and self.basal_candidates is not None
        return max(1, self.foldback.parts * self.basal_candidates.parts)

    @property
    def empty_foldback(self) -> bool:
        return self.foldback is not None and self.foldback.parts == 0

    @property
    def empty_local(self) -> bool:
        return self.empty_foldback or (self.basal is not None and self.basal.parts == 0)

    def depth(self, page: int) -> int:
        if type(page) is not int or not 0 <= page < self.count:
            raise ValueError("Survey local-page address lies outside the candidate domain.")
        if self.conflict is not None or self.empty_candidates:
            return 0
        assert self.foldback is not None and self.basal_candidates is not None
        return sum(coordinate_at((self.foldback.parts, self.basal_candidates.parts), page))

    def pages_at_depth(self, depth: int, *, after: int = -1) -> Iterator[int]:
        if (
            type(depth) is not int
            or depth < 0
            or type(after) is not int
            or not -1 <= after < self.count
        ):
            raise ValueError(
                "Local page seek requires a nonnegative depth and in-range predecessor."
            )
        if self.conflict is not None or self.empty_candidates:
            if depth == 0 and after < 0:
                yield 0
            return
        assert self.foldback is not None and self.basal_candidates is not None
        sizes = (self.foldback.parts, self.basal_candidates.parts)
        first = max(0, depth - sizes[1] + 1)
        if after >= 0:
            previous = coordinate_at(sizes, after)
            if sum(previous) > depth:
                return
            if sum(previous) == depth:
                first = max(first, previous[0] + 1)
        for fi in range(first, min(sizes[0] - 1, depth) + 1):
            yield coordinate_rank(sizes, (fi, depth - fi))

    def product(self, product: ProductRequest, page: int) -> ProductRequest:
        if type(page) is not int or not 0 <= page < self.count:
            raise ValueError("Survey local-page address lies outside the candidate domain.")
        if self.conflict is not None or self.empty_candidates:
            return product
        assert self.foldback is not None and self.basal_candidates is not None
        fi, bi = coordinate_at((self.foldback.parts, self.basal_candidates.parts), page)
        return self.basal_candidates.select(self.foldback.select(product, fi), bi)


class PartitionPlans:
    """Small invocation-owned cache, keyed by every local request dependency."""

    def __init__(
        self,
        index: SurveyIndex | None = None,
        limits: SequenceSpaceLimits | None = None,
        *,
        request: InterfaceSurveyRequest | None = None,
    ) -> None:
        if index is not None:
            if request is not None and request != index.request:
                raise ValueError("Partition request disagrees with its checkpoint.")
            request = index.request
        self._request = request
        self._plans: OrderedDict[str, ProductParts] = OrderedDict()
        self._locals: OrderedDict[str, BasalPopulation] = OrderedDict()
        self._populations: OrderedDict[str, tuple[FoldbackPopulation, int]] = OrderedDict()
        self._population_bytes = 0
        self._contexts: OrderedDict[str, ContextPriority] = OrderedDict()
        self._basal_admissions: BasalAdmissions | None = None
        self._index = index
        self._limits = default_sequence_limits() if limits is None else limits
        self._end_pairs = (
            EndPairRelations(request.materialization.source_preparation.source_ssdna, self._limits)
            if request is not None
            and request.source_context_objective == "paired_scaffold_completions"
            else None
        )

    def _population(self, local: LocalNeighborhoodRequest) -> FoldbackPopulation:
        request = population_request(local, self._limits)
        key = sha256_digest(canonical_json_bytes(request))
        if key in self._populations:
            self._populations.move_to_end(key)
            return self._populations[key][0]
        population = admit_population(request, self._index)
        size = len(canonical_json_bytes(population.result))
        if size <= _POPULATION_CACHE_BYTES:
            self._populations[key] = population, size
            self._population_bytes += size
            while (
                len(self._populations) > _POPULATION_CACHE_ENTRIES
                or self._population_bytes > _POPULATION_CACHE_BYTES
            ):
                _, (_, removed_size) = self._populations.popitem(last=False)
                self._population_bytes -= removed_size
        return population

    def _basal(self, request: LocalNeighborhoodRequest) -> BasalPopulation:
        key = sha256_digest(canonical_json_bytes(request))
        if key not in self._locals:
            self._locals[key] = admit_basal_population(request, self._limits)
        self._locals.move_to_end(key)
        while len(self._locals) > 8:
            self._locals.popitem(last=False)
        return self._locals[key]

    def end_pair_admission(self, product: ProductRequest) -> EndPairAdmission | None:
        """Necessary basal/end check only; no foldback expansion or route claim."""
        return None if self._end_pairs is None else self._end_pairs.assess(product)

    def foldback_population(self, product: ProductRequest) -> FoldbackPopulation:
        """Admit the exact foldback and its source-primer obligation independently."""
        local = product.construction_source().foldback
        return self._population(local).for_source_preparation(
            product.materialization.source_preparation
        )

    def frame_admission(
        self,
        branches: SurveyBranches,
        limits: SurveyEvaluationLimits,
        target: int,
        geometry: tuple[int, ...],
    ) -> EndPairAdmission | None:
        """Reuse only necessary joint facts under the same immutable request."""
        if self._end_pairs is None:
            return None
        if (
            self._basal_admissions is None
            or self._basal_admissions.branches is not branches
            or self._basal_admissions.limits != limits
        ):
            if branches.request != self._request:
                raise ValueError("Basal admission request differs from its invocation.")
            self._basal_admissions = BasalAdmissions(branches, limits, self._end_pairs)
        return self._basal_admissions.assess(target, geometry)

    def get(self, product: ProductRequest) -> ProductParts:
        key = sha256_digest(canonical_json_bytes(product))
        if key not in self._plans:
            admission = self.end_pair_admission(product)
            if admission is not None and not admission.requested_pair_admitted:
                plan = ProductParts(end_pair_admission=admission)
            else:
                try:
                    source = product.construction_source()
                except ProductConstraintConflict as conflict:
                    plan = ProductParts(conflict=conflict)
                else:
                    assert source.basal is not None
                    population = self._population(source.foldback).for_source_preparation(
                        product.materialization.source_preparation
                    )
                    basal = None if population.parts == 0 else self._basal(source.basal)
                    endpoint = None
                    if (
                        basal is not None
                        and basal.parts
                        and self._request is not None
                        and self._request.source_context_objective == "paired_scaffold_completions"
                    ):
                        # Bind every authored context, not the exact representative
                        # selected for this branch. Candidate pages must be invariant
                        # across auxiliary completions of the same scaffold.
                        endpoint = condition_population(
                            product,
                            basal,
                            self._request.materialization.source_preparation.source_ssdna,
                            self._limits,
                        )
                    plan = ProductParts(
                        population, basal, endpoint=endpoint, end_pair_admission=admission
                    )
            self._plans[key] = plan
        self._plans.move_to_end(key)
        while len(self._plans) > 8:
            self._plans.popitem(last=False)
        return self._plans[key]

    def context_priority(
        self, product: ProductRequest, page: int, policy: SourceSsdnaPolicy
    ) -> ContextPriority:
        plan = self.get(product)
        hint = None
        if plan.conflict is None and not plan.empty_candidates:
            assert plan.foldback is not None and plan.basal_candidates is not None
            _, bi = coordinate_at((plan.foldback.parts, plan.basal_candidates.parts), page)
            hint = basal_context_hint(product, plan.basal_candidates, bi)
        # Foldback pages can share this exact source action. Cache its full
        # dependencies rather than repeating the same work for each page ID.
        key = sha256_digest(
            canonical_json_bytes(
                {
                    "policy": policy.model_dump(mode="json"),
                    "hint": None
                    if hint is None
                    else {
                        "source_sequence": hint.source_sequence,
                        "payload_boundary_nt": hint.payload_boundary_nt,
                        "enzyme": hint.enzyme.model_dump(mode="json"),
                        "action": hint.action.model_dump(mode="json"),
                    },
                }
            )
        )
        if key not in self._contexts:
            self._contexts[key] = ContextPriority(policy, hint, self._limits)
        self._contexts.move_to_end(key)
        while len(self._contexts) > 8:
            self._contexts.popitem(last=False)
        return self._contexts[key]

    def first_page(
        self, branches: SurveyBranches, limits: SurveyEvaluationLimits, target: int
    ) -> tuple[int, int]:
        product = branches.product(target, branch=0, limits=limits)
        policy = branches.request.materialization.source_preparation.source_ssdna
        return self.context_priority(product, 0, policy).rank_at(0) * branches.geometry_count, 0
