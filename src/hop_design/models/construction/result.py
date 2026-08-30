"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/result.py

Defines payload-centered construction contracts and discovery evidence.

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
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    ProjectionInventoryItem,
    RealizationGroup,
    RealizationGrouping,
    RelaxationShellSummary,
    SearchCompletionStatus,
)
from .payload import _content_id
from .realization import ConstructionExecution, LocalRealization
from .relaxation import RelaxationMode, geometry_coordinate_value, geometry_fixed_projection
from .request import LocalNeighborhoodRequest, geometry_id, problem_id


class NeighborhoodDiscoveryResult(HopModel):
    """Exact local realizations with explicit bounded-search completion evidence."""

    schema_id: Literal["hop.neighborhood-discovery-result/v3"] = Field(
        default="hop.neighborhood-discovery-result/v3", alias="schema"
    )
    status: SearchCompletionStatus
    request: LocalNeighborhoodRequest
    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    execution_id: str = Field(pattern=r"^hop:execution/[0-9a-f]{64}@1$")
    execution: ConstructionExecution
    shells: tuple[RelaxationShellSummary, ...] = Field(min_length=1)
    realizations: tuple[LocalRealization, ...]
    achieved_geometry_groups: tuple[RealizationGroup, ...]
    rejected_count: int = Field(ge=0)
    failure_reasons: tuple[FailureReasonCount, ...]
    payload_compatibility: PayloadCompatibilityAccounting
    provenance: NeighborhoodProvenance
    projection_inventory: tuple[ProjectionInventoryItem, ...]
    claim_boundary: NeighborhoodClaimBoundary
    truncation_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> NeighborhoodDiscoveryResult:
        if self.problem_id != problem_id(self.request):
            raise ValueError("problem_id must replay from the local request.")
        if (
            self.execution.problem_id != self.problem_id
            or self.execution.enumeration != self.request.enumeration
            or self.execution.max_operations != self.request.enzyme_provisioning.max_operations
            or self.execution.execution_id != self.execution_id
        ):
            raise ValueError("Embedded execution must replay the exact local request.")
        if (
            self.provenance.hop_version != self.execution.hop_version
            or self.provenance.route_implementation_version
            != self.execution.route_implementation_version
        ):
            raise ValueError("Local result provenance must equal embedded execution versions.")
        payload_cardinality = 1
        for symbol in self.request.payload.payload.sequence:
            payload_cardinality *= len(iupac_bases(symbol))
        if self.payload_compatibility.total_assignments != payload_cardinality:
            raise ValueError(
                "Payload accounting must replay the exact request payload cardinality."
            )
        partitioned = self.request.enumeration.sequence_partition is not None
        if (
            partitioned
            and self.payload_compatibility.status is not PayloadCompatibilityStatus.NOT_COMPUTED
        ):
            raise ValueError(
                "A sequence-domain part cannot claim whole-domain payload compatibility."
            )
        radii = tuple(shell.radius for shell in self.shells)
        if not radii or radii[0] != 0 or radii != tuple(range(len(radii))):
            raise ValueError("Examined relaxation shells must be contiguous and exact-first.")
        if not all(shell.examined for shell in self.shells):
            raise ValueError("Recorded relaxation shells must have been examined.")
        incomplete_shells = tuple(
            index for index, shell in enumerate(self.shells) if not shell.complete
        )
        if incomplete_shells and incomplete_shells != (len(self.shells) - 1,):
            raise ValueError("Only the final recorded shell may be incomplete.")
        if self.status is not SearchCompletionStatus.TRUNCATED and incomplete_shells:
            raise ValueError("Complete and infeasible results require complete recorded shells.")
        realization_ids = tuple(item.local_realization_id for item in self.realizations)
        if len(realization_ids) != len(set(realization_ids)):
            raise ValueError("A local result must not repeat an exact realization.")
        shell_ids = tuple(
            realization_id for shell in self.shells for realization_id in shell.realization_ids
        )
        if shell_ids != realization_ids:
            raise ValueError(
                "Relaxation shells must preserve the ordered local realization relation."
            )
        shell_by_realization_id = {
            realization_id: shell.radius
            for shell in self.shells
            for realization_id in shell.realization_ids
        }
        for realization in self.realizations:
            actual_radius = self._realization_relaxation_radius(realization)
            if shell_by_realization_id[realization.local_realization_id] != actual_radius:
                raise ValueError(
                    "Each local realization must belong to its declared relaxation shell."
                )
        if self.status is SearchCompletionStatus.TRUNCATED and not self.truncation_reasons:
            raise ValueError("Truncated results require truncation reasons.")
        if self.status is not SearchCompletionStatus.TRUNCATED and self.truncation_reasons:
            raise ValueError("Only truncated results may contain truncation reasons.")
        if self.status is SearchCompletionStatus.INFEASIBLE and self.realizations:
            raise ValueError("Infeasible results must not contain realizations.")
        if self.status is SearchCompletionStatus.COMPLETE and not self.realizations:
            raise ValueError("A complete local result must contain at least one realization.")
        failure_codes = tuple(item.code for item in self.failure_reasons)
        if len(failure_codes) != len(set(failure_codes)):
            raise ValueError("Failure-reason codes must be unique.")
        if failure_codes != tuple(sorted(failure_codes)):
            raise ValueError("Failure reasons must use canonical code order.")
        shell_rejected_count = sum(shell.rejected_count for shell in self.shells)
        if shell_rejected_count != self.rejected_count:
            raise ValueError("Shell rejected candidates must sum to the global rejected count.")
        shell_failures: Counter[str] = Counter()
        for shell in self.shells:
            shell_failures.update({reason.code: reason.count for reason in shell.failure_reasons})
        global_failures = Counter({reason.code: reason.count for reason in self.failure_reasons})
        if shell_failures != global_failures:
            raise ValueError("Shell failure reasons must aggregate to global failure reasons.")
        if self.provenance.enzyme_catalog_digest != self.request.enzyme_catalog_digest:
            raise ValueError("Result provenance must bind the request enzyme-catalog digest.")
        if (
            self.request.hard_constraints.require_all_members_compatible
            and self.payload_compatibility.status is PayloadCompatibilityStatus.COMPLETE
            and self.payload_compatibility.excluded_assignments
            and self.realizations
        ):
            raise ValueError(
                "All-member compatibility forbids realizations when any payload is excluded."
            )
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
        realizations_by_id = {
            realization.local_realization_id: realization for realization in self.realizations
        }
        for group in self.achieved_geometry_groups:
            member_geometry_ids = {
                geometry_id(realizations_by_id[member].achieved_geometry)
                for member in group.realization_ids
            }
            if member_geometry_ids != {group.group_key}:
                raise ValueError("Achieved-geometry group key must match every member realization.")
            expected_members = tuple(
                realization.local_realization_id
                for realization in self.realizations
                if geometry_id(realization.achieved_geometry) == group.group_key
            )
            if group.realization_ids != expected_members:
                raise ValueError(
                    "Achieved-geometry groups must preserve realization order within each group."
                )
        if self.claim_boundary.method is not MethodResolutionStatus.NOT_RESOLVED:
            raise ValueError(
                "Local neighborhood discovery cannot claim a material-bound method resolution."
            )
        required_radius = self._required_completion_radius()
        if (
            self.status is SearchCompletionStatus.TRUNCATED
            and not incomplete_shells
            and radii[-1] >= required_radius
        ):
            raise ValueError(
                "All-complete truncation requires an unentered later shell in the declared domain."
            )
        if radii[-1] > required_radius:
            raise ValueError(
                "A result must not record shells beyond the declared relaxation domain."
            )
        if self.status is SearchCompletionStatus.INFEASIBLE and radii[-1] != required_radius:
            raise ValueError("Infeasible results must examine all declared relaxation shells.")
        if (
            self.status is SearchCompletionStatus.COMPLETE
            and self.request.relaxation.mode is RelaxationMode.THROUGH_RADIUS
            and radii[-1] != required_radius
        ):
            raise ValueError("through_radius results must examine all declared relaxation shells.")
        if (
            self.status is SearchCompletionStatus.COMPLETE
            and self.request.relaxation.mode is RelaxationMode.FIRST_FEASIBLE_SHELL
        ):
            hit_shells = tuple(shell.radius for shell in self.shells if shell.realization_ids)
            if self.request.hard_constraints.require_all_members_compatible:
                if (
                    not hit_shells
                    or hit_shells[-1] != radii[-1]
                    or self.payload_compatibility.compatible_assignments
                    != self.payload_compatibility.total_assignments
                ):
                    raise ValueError(
                        "All-member first-feasible search must stop at the first shell "
                        "that completes payload compatibility."
                    )
            elif hit_shells != (radii[-1],):
                raise ValueError(
                    "first_feasible_shell must stop at the first shell with realizations."
                )
        if self.status is SearchCompletionStatus.TRUNCATED:
            expected_reason = self._execution_truncation_reason()
            if self.truncation_reasons != (expected_reason,):
                raise ValueError(
                    "Truncated results require the canonical truncation reasons from execution "
                    "bounds."
                )
        return self

    def _realization_relaxation_radius(self, realization: LocalRealization) -> int:
        target = self.request.target
        achieved = realization.achieved_geometry
        if type(achieved) is not type(target) or achieved.family != self.request.family.value:
            raise ValueError("A local realization must use the requested neighborhood family.")
        coordinate_names = {coordinate.name for coordinate in self.request.relaxation.coordinates}
        target_projection = geometry_fixed_projection(target, coordinate_names)
        achieved_projection = geometry_fixed_projection(achieved, coordinate_names)
        if target_projection.get("nick_strand") == "any":
            target_projection["nick_strand"] = achieved_projection.get("nick_strand")
        if target_projection != achieved_projection:
            raise ValueError("A local realization changed a non-enabled geometry field.")
        radius = 0
        for coordinate in self.request.relaxation.coordinates:
            achieved_value = geometry_coordinate_value(achieved, coordinate.name)
            if not coordinate.minimum <= achieved_value <= coordinate.maximum:
                raise ValueError("A local realization lies outside the declared relaxation bounds.")
            radius += abs(achieved_value - geometry_coordinate_value(target, coordinate.name))
        if radius > self.request.relaxation.max_radius:
            raise ValueError("A local realization lies outside the declared relaxation radius.")
        return radius

    def _required_completion_radius(self) -> int:
        target = self.request.target
        reachable_radius = sum(
            max(
                abs(geometry_coordinate_value(target, coordinate.name) - coordinate.minimum),
                abs(coordinate.maximum - geometry_coordinate_value(target, coordinate.name)),
            )
            for coordinate in self.request.relaxation.coordinates
        )
        return min(self.request.relaxation.max_radius, reachable_radius)

    def _execution_truncation_reason(self) -> str | None:
        examined = sum(shell.candidate_count for shell in self.shells)
        if examined > self.execution.enumeration.max_search_nodes:
            raise ValueError("Local search accounting exceeds max_search_nodes.")
        if len(self.realizations) > self.execution.enumeration.max_realizations:
            raise ValueError("Local search accounting exceeds max_realizations.")
        if examined == self.execution.enumeration.max_search_nodes:
            return "max_search_nodes"
        if len(self.realizations) == self.execution.enumeration.max_realizations:
            return "max_realizations"
        return None

    @property
    def result_id(self) -> str:
        """Return identity for the ordered result relation and status."""
        return _content_id(
            "neighborhood-result",
            1,
            {
                "schema": self.schema_id,
                "problem_id": self.problem_id,
                "execution_id": self.execution_id,
                "status": self.status,
                "shells": [shell.model_dump(mode="json") for shell in self.shells],
                "realization_ids": [
                    realization.local_realization_id for realization in self.realizations
                ],
                "achieved_geometry_groups": [
                    group.model_dump(mode="json") for group in self.achieved_geometry_groups
                ],
                "rejected_count": self.rejected_count,
                "failure_reasons": [
                    reason.model_dump(mode="json") for reason in self.failure_reasons
                ],
                "payload_compatibility": self.payload_compatibility.model_dump(mode="json"),
                "provenance": self.provenance.model_dump(mode="json"),
                "truncation_reasons": self.truncation_reasons,
            },
        )
