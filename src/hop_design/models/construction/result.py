"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/result.py

Defines retained-overhead neighborhood search authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import iupac_bases

from .accounting import (
    FailureReasonCount,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    NeighborhoodProvenance,
    OverheadLevelSummary,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    ProjectionInventoryItem,
    RealizationGroup,
    RealizationGrouping,
    SearchCompletionStatus,
    SearchDisposition,
    SearchFeasibilityStatus,
)
from .payload import _content_id
from .realization import ConstructionExecution, LocalRealization
from .request import LocalNeighborhoodRequest, geometry_id, problem_id


class NeighborhoodDiscoveryResult(HopModel):
    """Exact local realizations with explicit coverage and feasibility evidence."""

    schema_id: Literal["hop.neighborhood-discovery-result/v5"] = Field(
        default="hop.neighborhood-discovery-result/v5", alias="schema"
    )
    disposition: SearchDisposition
    request: LocalNeighborhoodRequest
    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    execution_id: str = Field(pattern=r"^hop:execution/[0-9a-f]{64}@1$")
    execution: ConstructionExecution
    overhead_levels: tuple[OverheadLevelSummary, ...] = Field(min_length=1)
    realizations: tuple[LocalRealization, ...]
    achieved_geometry_groups: tuple[RealizationGroup, ...]
    rejected_count: int = Field(ge=0)
    failure_reasons: tuple[FailureReasonCount, ...]
    payload_compatibility: PayloadCompatibilityAccounting
    provenance: NeighborhoodProvenance
    projection_inventory: tuple[ProjectionInventoryItem, ...]
    claim_boundary: NeighborhoodClaimBoundary

    @model_validator(mode="after")
    def validate_result(self) -> NeighborhoodDiscoveryResult:
        self._validate_execution()
        self._validate_payload_accounting()
        self._validate_level_coverage()
        realization_ids = self._validate_realization_membership()
        self._validate_failure_accounting()
        self._validate_groups(realization_ids)
        self._validate_disposition(realization_ids)
        if self.claim_boundary.method is not MethodResolutionStatus.NOT_RESOLVED:
            raise ValueError(
                "Local neighborhood discovery cannot claim a material-bound method resolution."
            )
        return self

    def _validate_execution(self) -> None:
        if self.problem_id != problem_id(self.request):
            raise ValueError("problem_id must replay from the local request.")
        if (
            self.execution.problem_id != self.problem_id
            or self.execution.search != self.request.search
            or self.execution.max_operations != self.request.enzyme_provisioning.max_operations
            or self.execution.execution_id != self.execution_id
        ):
            raise ValueError("Embedded execution must replay the exact local request.")
        if (
            self.provenance.hop_version != self.execution.hop_version
            or self.provenance.route_implementation_version
            != self.execution.route_implementation_version
            or self.provenance.enzyme_catalog_digest != self.request.enzyme_catalog_digest
        ):
            raise ValueError("Local result provenance must equal its execution and catalog.")

    def _validate_payload_accounting(self) -> None:
        payload_cardinality = 1
        for symbol in self.request.payload.payload.sequence:
            payload_cardinality *= len(iupac_bases(symbol))
        if self.payload_compatibility.total_assignments != payload_cardinality:
            raise ValueError(
                "Payload accounting must replay the exact request payload cardinality."
            )
        if (
            self.request.search.sequence_partition is not None
            and self.payload_compatibility.status is not PayloadCompatibilityStatus.NOT_COMPUTED
        ):
            raise ValueError(
                "A sequence-domain part cannot claim whole-domain payload compatibility."
            )
        if (
            self.request.hard_constraints.require_all_members_compatible
            and self.payload_compatibility.status is PayloadCompatibilityStatus.COMPLETE
            and self.payload_compatibility.excluded_assignments
            and self.realizations
        ):
            raise ValueError(
                "All-member compatibility forbids realizations when any payload is excluded."
            )

    def _validate_level_coverage(self) -> None:
        overheads = tuple(level.retained_overhead_nt for level in self.overhead_levels)
        if overheads != tuple(range(len(overheads))):
            raise ValueError("Recorded retained-overhead levels must be contiguous from zero.")
        if overheads[-1] > self.request.search.max_retained_overhead_nt:
            raise ValueError("A result must not exceed its retained-overhead envelope.")
        if not all(level.examined for level in self.overhead_levels):
            raise ValueError("Recorded retained-overhead levels must have been examined.")
        incomplete = tuple(
            index for index, level in enumerate(self.overhead_levels) if not level.complete
        )
        if incomplete and incomplete != (len(self.overhead_levels) - 1,):
            raise ValueError("Only the final recorded overhead level may be incomplete.")
        if self.disposition.completion is SearchCompletionStatus.COMPLETE and (
            incomplete or overheads[-1] != self.request.search.max_retained_overhead_nt
        ):
            raise ValueError("Complete coverage must exhaust the retained-overhead envelope.")
        if (
            self.disposition.completion is SearchCompletionStatus.TRUNCATED
            and not incomplete
            and overheads[-1] == self.request.search.max_retained_overhead_nt
        ):
            raise ValueError("Truncated coverage requires unresolved work in the declared domain.")

    def _validate_realization_membership(self) -> tuple[str, ...]:
        realization_ids = tuple(item.local_realization_id for item in self.realizations)
        if len(realization_ids) != len(set(realization_ids)):
            raise ValueError("A local result must not repeat an exact realization.")
        level_ids = tuple(
            realization_id
            for level in self.overhead_levels
            for realization_id in level.realization_ids
        )
        if level_ids != realization_ids:
            raise ValueError(
                "Retained-overhead levels must preserve the ordered realization relation."
            )
        return realization_ids

    def _validate_failure_accounting(self) -> None:
        failure_codes = tuple(item.code for item in self.failure_reasons)
        if len(failure_codes) != len(set(failure_codes)) or failure_codes != tuple(
            sorted(failure_codes)
        ):
            raise ValueError("Failure reasons must use unique canonical code order.")
        if sum(level.rejected_count for level in self.overhead_levels) != self.rejected_count:
            raise ValueError("Overhead-level rejections must sum to the global rejected count.")
        level_failures: Counter[str] = Counter()
        for level in self.overhead_levels:
            level_failures.update({reason.code: reason.count for reason in level.failure_reasons})
        if level_failures != Counter(
            {reason.code: reason.count for reason in self.failure_reasons}
        ):
            raise ValueError("Overhead-level failures must aggregate to global failure reasons.")

    def _validate_groups(self, realization_ids: tuple[str, ...]) -> None:
        inventory_keys = tuple(
            (item.projection_schema, item.renderer_version) for item in self.projection_inventory
        )
        if len(inventory_keys) != len(set(inventory_keys)):
            raise ValueError("Projection inventory entries must be unique by schema and renderer.")
        grouped_ids = tuple(
            member for group in self.achieved_geometry_groups for member in group.realization_ids
        )
        if any(
            group.grouping is not RealizationGrouping.ACHIEVED_GEOMETRY
            for group in self.achieved_geometry_groups
        ):
            raise ValueError("Neighborhood results may embed only achieved-geometry groups.")
        if Counter(grouped_ids) != Counter(realization_ids) or len(grouped_ids) != len(
            set(grouped_ids)
        ):
            raise ValueError("Achieved-geometry groups must cover every realization exactly once.")
        group_keys = tuple(group.group_key for group in self.achieved_geometry_groups)
        if group_keys != tuple(sorted(group_keys)):
            raise ValueError("Achieved-geometry groups must use canonical key order.")
        realizations = {item.local_realization_id: item for item in self.realizations}
        for group in self.achieved_geometry_groups:
            if {
                geometry_id(realizations[member].achieved_geometry)
                for member in group.realization_ids
            } != {group.group_key}:
                raise ValueError("Achieved-geometry group key must match every realization.")
            expected = tuple(
                item.local_realization_id
                for item in self.realizations
                if geometry_id(item.achieved_geometry) == group.group_key
            )
            if group.realization_ids != expected:
                raise ValueError("Geometry groups must preserve realization order.")

    def _validate_disposition(self, realization_ids: tuple[str, ...]) -> None:
        feasible = self.disposition.feasibility is SearchFeasibilityStatus.FEASIBLE
        if feasible != bool(realization_ids):
            raise ValueError("Search feasibility must agree with accepted realizations.")
        if (
            self.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
            and self.disposition.completion is not SearchCompletionStatus.COMPLETE
        ):
            raise ValueError("Only complete coverage can establish infeasibility.")
        examined = sum(level.candidate_count for level in self.overhead_levels)
        if examined > self.execution.search.max_search_nodes:
            raise ValueError("Local search accounting exceeds max_search_nodes.")
        if len(realization_ids) > self.execution.search.max_realizations:
            raise ValueError("Local search accounting exceeds max_realizations.")

    @property
    def result_id(self) -> str:
        """Return identity for the ordered result relation and disposition."""
        return _content_id(
            "neighborhood-result",
            1,
            {
                "schema": self.schema_id,
                "problem_id": self.problem_id,
                "execution_id": self.execution_id,
                "disposition": self.disposition.model_dump(mode="json"),
                "overhead_levels": [
                    level.model_dump(mode="json") for level in self.overhead_levels
                ],
                "realization_ids": [item.local_realization_id for item in self.realizations],
                "achieved_geometry_groups": [
                    group.model_dump(mode="json") for group in self.achieved_geometry_groups
                ],
                "rejected_count": self.rejected_count,
                "failure_reasons": [
                    reason.model_dump(mode="json") for reason in self.failure_reasons
                ],
                "payload_compatibility": self.payload_compatibility.model_dump(mode="json"),
                "provenance": self.provenance.model_dump(mode="json"),
            },
        )
