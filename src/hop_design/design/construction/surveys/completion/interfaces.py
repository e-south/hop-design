"""Invocation-owned, bounded reuse of necessary end-pair relations."""

import json
from collections import OrderedDict
from dataclasses import dataclass

from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain
from hop_design.kernel.construction.basal.programs import BasalPlacementFailure
from hop_design.kernel.construction.release_constraints import release_frame_supported
from hop_design.kernel.construction.release_pair_relation import necessary_end_pairs
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    SourceSsdnaPolicy,
)
from hop_design.models.construction.product_pairing import ProductConstraintConflict
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.request import LocalNeighborhoodRequest
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits
from hop_design.models.enzymes import EnzymeProvisioningPolicy, EnzymeRole
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...basal.traversal import iter_basal_work_units


@dataclass(frozen=True)
class EndPairAdmission:
    requested_pair_admitted: bool
    permitted_pair_count: int
    relation_digest: str

    def facts(self) -> dict[str, object]:
        return {
            "scope": "necessary_end_pair_relation",
            "requested_pair_admitted": self.requested_pair_admitted,
            "permitted_pair_count": self.permitted_pair_count,
            "relation_digest": self.relation_digest,
        }


class EndPairRelations:
    """Preserve the complete template, normalizing only exact end words and context.

    Values are necessary relations, not cached constructions or reusable proof
    certificates. Eviction affects speed only. Every new invocation recomputes.
    """

    def __init__(self, policy: SourceSsdnaPolicy, limits: SequenceSpaceLimits):
        self.policy, self.limits = policy, limits
        self._cache: OrderedDict[str, tuple[SequenceSet | None, int]] = OrderedDict()
        self._bytes = 0

    def assess(self, product: ProductRequest) -> EndPairAdmission | None:
        relation = self.relation(product)
        if relation is None:
            return None
        assert product.ends is not None
        word = product.ends.left.cohesive_end_sequence + product.ends.right.cohesive_end_sequence
        return EndPairAdmission(
            relation.contains(word),
            relation.cardinality,
            sha256_digest(canonical_json_bytes(relation)),
        )

    def relation(self, product: ProductRequest) -> SequenceSet | None:
        if (
            not isinstance(self.policy, ConstrainedSourceSsdnaPolicy)
            or not release_frame_supported(product)
            or product.release is None
            or product.ends is None
            or product.basal is None
            or product.basal.geometry.minimum_adapter_annealing_nt is None
            or product.release.basal_projection.product_end != "right"
            or product.ends.left.orientation.value != "forward"
            or product.ends.right.orientation.value != "reverse"
            or any(
                e.overhang_end.value != "five_prime"
                for e in (product.ends.left, product.ends.right)
            )
        ):
            return None
        permissions = EnzymeProvisioningPolicy(
            **product.release.enzymes.model_dump(),
            catalog=product.enzyme_catalog,
        )
        if (
            sum(
                permissions.permits(e.enzyme_id, role=EnzymeRole.END_GENERATION)
                for e in product.enzyme_catalog.enzymes
            )
            != 1
        ):
            return None  # Different enzymes at the two ends are not yet translated.
        data = product.model_dump(mode="json", by_alias=True)
        # The proven frame omits the folded interior. Its geometry and display
        # name cannot change this necessary relation; full compilation still can.
        data.pop("foldback")
        data.pop("name", None)
        for side in ("left", "right"):
            word = data["ends"][side]["cohesive_end_sequence"]
            data["ends"][side]["cohesive_end_sequence"] = "N" * len(word)
        data["materialization"]["source_preparation"]["source_ssdna"] = self.policy.model_dump(
            mode="json"
        )
        key = sha256_digest(canonical_json_bytes(data))
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key][0]
        try:
            local = product.construction_source().basal
            assert local is not None
            data = local.model_dump(mode="json", by_alias=True)
            data["geometry_domain"]["pairing_constraints"] = [
                c.model_dump(mode="json") for c in product.expanded_pairing_constraints()
            ]
            data["search"]["sequence_partition"] = None
            local = LocalNeighborhoodRequest.model_validate_json(json.dumps(data))
        except ProductConstraintConflict:
            return None  # Ordinary admission owns exact request contradictions.
        domains = []
        for overhead in range(local.search.max_retained_overhead_nt + 1):
            for unit in iter_basal_work_units(local, retained_overhead_nt=overhead):
                domain = solve_basal_sequence_domain(
                    payload_sequence=unit.payload_sequence,
                    target=unit.target,
                    endpoint=product.endpoint,
                    program=unit.program,
                    defer_end_sequence=True,
                )
                if not isinstance(domain, BasalPlacementFailure):
                    domains.append(domain)
        result = necessary_end_pairs(product, tuple(domains), self.policy, self.limits)
        size = 0 if result is None else len(canonical_json_bytes(result))
        if size <= 2 * 1024 * 1024:
            self._cache[key] = result, size
            self._bytes += size
            while len(self._cache) > 4096 or self._bytes > 2 * 1024 * 1024:
                _, (_, removed) = self._cache.popitem(last=False)
                self._bytes -= removed
        return result
