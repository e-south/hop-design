"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/complete.py

Defines a lossless scientific summary of verified whole-route composition.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Literal, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import (
    FailureReasonCount,
    NeighborhoodClaimBoundary,
    RealizationGroup,
    RealizationGrouping,
    SearchCompletionStatus,
)
from hop_design.models.construction.complete.accounting import CompositionAccounting
from hop_design.models.construction.complete.authority import (
    CompositionDispositionStatus,
    CompositionMaterialAccounting,
    ConstructionCompositionProvenance,
)
from hop_design.models.construction.complete.evaluation import CompositionRejectionCode
from hop_design.models.construction.complete.material_disposition import (
    RouteMaterialDispositionSpan,
)
from hop_design.models.construction.payload import ConstructionEndpoint, _content_id

COMPLETE_CONSTRUCTION_PROJECTION_RENDERER_VERSION: Literal[
    "complete-construction-projections/1"
] = "complete-construction-projections/1"


class CompleteConstructionSummaryRow(HopModel):
    """One exact ordered composition disposition and its accepted-route facts."""

    ordinal: int = Field(ge=0)
    foldback_realization_id: str = Field(pattern=r"^hop:foldback-realization/[0-9a-f]{64}@1$")
    basal_realization_id: str | None = Field(
        default=None,
        pattern=r"^hop:basal-realization/[0-9a-f]{64}@1$",
    )
    status: CompositionDispositionStatus
    rejection_reason: CompositionRejectionCode | None = None
    materialized_realization_id: str | None = Field(
        default=None,
        pattern=r"^hop:materialized-construction/[0-9a-f]{64}@1$",
    )
    achieved_geometry_group_key: str | None = Field(
        default=None,
        pattern=r"^hop:geometry/[0-9a-f]{64}@1$",
    )
    final_product_group_key: str | None = Field(
        default=None,
        pattern=r"^hop:final-product/[0-9a-f]{64}@1$",
    )
    endpoint: ConstructionEndpoint | None = None
    material_ids: tuple[str, ...] = ()
    route_material_dispositions: tuple[RouteMaterialDispositionSpan, ...] = ()
    source_material_nt: int = Field(default=0, ge=0)
    auxiliary_material_nt: int = Field(default=0, ge=0)
    endpoint_product_nt: int = Field(default=0, ge=0)
    candidate_enzyme_programs: int = Field(ge=0)
    recognition_placements_attempted: int = Field(ge=0)
    constraint_systems_attempted: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_disposition(self) -> CompleteConstructionSummaryRow:
        accepted_facts = (
            self.materialized_realization_id,
            self.achieved_geometry_group_key,
            self.final_product_group_key,
            self.endpoint,
        )
        if self.status is CompositionDispositionStatus.ACCEPTED:
            if self.rejection_reason is not None or any(item is None for item in accepted_facts):
                raise ValueError("Accepted summary rows require exact route and grouping facts.")
            if (
                not self.material_ids
                or self.source_material_nt == 0
                or self.endpoint_product_nt == 0
            ):
                raise ValueError("Accepted summary rows require exact material accounting.")
        elif self.rejection_reason is None or any(item is not None for item in accepted_facts):
            raise ValueError(
                "Rejected summary rows require one reason and no accepted-route facts."
            )
        elif (
            self.material_ids
            or self.route_material_dispositions
            or self.source_material_nt
            or self.auxiliary_material_nt
            or self.endpoint_product_nt
        ):
            raise ValueError("Rejected summary rows cannot report materialized route evidence.")
        return self


class CompleteConstructionSummaryProjection(HopModel):
    """Lossless presentation relation over one verified construction-space result."""

    schema_id: Literal["hop.complete-construction-summary/v1"] = Field(
        default="hop.complete-construction-summary/v1",
        alias="schema",
    )
    projection_id: str = Field(pattern=r"^hop:complete-construction-summary/[0-9a-f]{64}@1$")
    source_result_id: str = Field(pattern=r"^hop:construction-space-result/[0-9a-f]{64}@1$")
    renderer_version: Literal["complete-construction-projections/1"] = (
        COMPLETE_CONSTRUCTION_PROJECTION_RENDERER_VERSION
    )
    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    execution_id: str = Field(pattern=r"^hop:construction-execution/[0-9a-f]{64}@1$")
    endpoint: ConstructionEndpoint
    status: SearchCompletionStatus
    rows: tuple[CompleteConstructionSummaryRow, ...]
    geometry_groups: tuple[RealizationGroup, ...]
    final_product_groups: tuple[RealizationGroup, ...]
    accounting: CompositionAccounting
    material_accounting: CompositionMaterialAccounting
    failure_reasons: tuple[FailureReasonCount, ...]
    truncation_reasons: tuple[str, ...]
    upstream_truncation_reasons: tuple[str, ...]
    provenance: ConstructionCompositionProvenance
    claim_boundary: NeighborhoodClaimBoundary

    @classmethod
    def create(cls, **content: object) -> CompleteConstructionSummaryProjection:
        draft = cls.model_construct(projection_id="", **cast(Any, content))
        return cls.model_validate({"projection_id": draft._expected_projection_id(), **content})

    def _expected_projection_id(self) -> str:
        return _content_id(
            "complete-construction-summary",
            1,
            self.model_dump(mode="json", by_alias=True, exclude={"projection_id"}),
        )

    @model_validator(mode="after")
    def validate_projection(self) -> CompleteConstructionSummaryProjection:
        if tuple(row.ordinal for row in self.rows) != tuple(range(len(self.rows))):
            raise ValueError("Complete summary rows must preserve exact disposition order.")
        if len(self.rows) != self.accounting.examined_combinations:
            raise ValueError("Complete summary rows must cover the exact examined prefix.")
        if any(row.endpoint is not None and row.endpoint is not self.endpoint for row in self.rows):
            raise ValueError("Accepted summary endpoints must match the requested endpoint.")
        accepted = tuple(
            cast(str, row.materialized_realization_id)
            for row in self.rows
            if row.status is CompositionDispositionStatus.ACCEPTED
        )
        if len(accepted) != len(set(accepted)):
            raise ValueError("Accepted summary realizations must be unique.")
        rejected = Counter(
            row.rejection_reason
            for row in self.rows
            if row.status is CompositionDispositionStatus.REJECTED
        )
        if len(accepted) != self.accounting.valid_realizations or sum(rejected.values()) != (
            self.accounting.rejected_combinations
        ):
            raise ValueError("Complete summary disposition counts must replay accounting.")
        if rejected != Counter({item.code: item.count for item in self.failure_reasons}):
            raise ValueError("Complete summary rejection rows must replay failure counts.")
        if (
            sum(row.candidate_enzyme_programs for row in self.rows)
            != (self.accounting.candidate_enzyme_programs)
            or sum(row.recognition_placements_attempted for row in self.rows)
            != (self.accounting.recognition_placements_attempted)
            or sum(row.constraint_systems_attempted for row in self.rows)
            != (self.accounting.constraint_systems_attempted)
        ):
            raise ValueError("Complete summary rows must replay route-attempt accounting.")
        self._validate_grouping(accepted, RealizationGrouping.ACHIEVED_GEOMETRY)
        self._validate_grouping(accepted, RealizationGrouping.FINAL_PRODUCT)
        if (
            len(self.geometry_groups) != self.accounting.distinct_geometry_groups
            or len(self.final_product_groups) != self.accounting.distinct_final_products
        ):
            raise ValueError("Complete summary group counts must replay accounting.")
        if self.material_accounting != CompositionMaterialAccounting(
            source_material_nt=sum(row.source_material_nt for row in self.rows),
            auxiliary_material_nt=sum(row.auxiliary_material_nt for row in self.rows),
            endpoint_product_nt=sum(row.endpoint_product_nt for row in self.rows),
        ):
            raise ValueError("Complete summary rows must replay exact material accounting.")
        if (
            self.status
            in {
                SearchCompletionStatus.COMPLETE,
                SearchCompletionStatus.INFEASIBLE,
            }
            and self.accounting.examined_combinations != self.accounting.nominal_combinations
        ):
            raise ValueError("Complete and infeasible summaries require exhaustive accounting.")
        if self.status is SearchCompletionStatus.COMPLETE and not accepted:
            raise ValueError("Complete summaries require at least one accepted realization.")
        if self.status is SearchCompletionStatus.INFEASIBLE and accepted:
            raise ValueError("Infeasible summaries cannot contain accepted realizations.")
        if self.status is SearchCompletionStatus.TRUNCATED:
            if not self.truncation_reasons and not self.upstream_truncation_reasons:
                raise ValueError("Truncated summaries require an exact truncation reason.")
        elif self.truncation_reasons or self.upstream_truncation_reasons:
            raise ValueError("Only truncated summaries may report truncation reasons.")
        if self.projection_id != self._expected_projection_id():
            raise ValueError("projection_id must seal the complete summary relation.")
        return self

    def _validate_grouping(
        self,
        accepted: tuple[str, ...],
        grouping: RealizationGrouping,
    ) -> None:
        groups = (
            self.geometry_groups
            if grouping is RealizationGrouping.ACHIEVED_GEOMETRY
            else self.final_product_groups
        )
        if any(group.grouping is not grouping for group in groups):
            raise ValueError("Complete summary group dimensions must remain explicit.")
        group_keys = tuple(group.group_key for group in groups)
        if group_keys != tuple(sorted(set(group_keys))):
            raise ValueError("Complete summary groups require unique canonical group keys.")
        grouped = tuple(member for group in groups for member in group.realization_ids)
        if Counter(grouped) != Counter(accepted):
            raise ValueError("Complete summary groups must losslessly cover accepted rows.")
        expected = {member: group.group_key for group in groups for member in group.realization_ids}
        observed = {
            cast(str, row.materialized_realization_id): (
                row.achieved_geometry_group_key
                if grouping is RealizationGrouping.ACHIEVED_GEOMETRY
                else row.final_product_group_key
            )
            for row in self.rows
            if row.status is CompositionDispositionStatus.ACCEPTED
        }
        if observed != expected:
            raise ValueError("Complete summary grouping keys must replay exact membership.")


__all__ = [
    "COMPLETE_CONSTRUCTION_PROJECTION_RENDERER_VERSION",
    "CompleteConstructionSummaryProjection",
    "CompleteConstructionSummaryRow",
]
