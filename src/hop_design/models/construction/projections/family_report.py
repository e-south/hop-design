"""Read-only family report facts; authority and preparation identities remain explicit."""

from typing import Literal

from pydantic import Field, JsonValue

from hop_design.models.base import HopModel
from hop_design.models.construction.family.controls import ComparisonControl

from .comparison import ConstructionComparisonProjection
from .product_stages import ProductStageProjection
from .sequence_difference import SequenceRegionDifference


class FamilyReportEdit(HopModel):
    source_member: str
    target_member: str
    requested_changes: dict[str, tuple[int | None, int | None]]
    effective_changes: dict[str, tuple[JsonValue, JsonValue]]


class FamilyReportComparison(HopModel):
    baseline_member: str
    member: str
    molecular: ConstructionComparisonProjection
    regions: tuple[SequenceRegionDifference, ...]


class FamilyReportChoice(HopModel):
    source_result_id: str
    materialized_realization_id: str
    geometry: dict[str, int]
    portrait: str
    preparation: str
    selected: bool
    selection_name: str | None = None
    stage: str
    stage_role: str
    endpoint: str
    shared_property_differences: tuple[JsonValue, ...]
    product_stages: ProductStageProjection
    stage_drawing: str
    closing_drawing: str


class FamilyReportMember(HopModel):
    name: str
    requested_variation: dict[str, int | None]
    effective_geometry: dict[str, JsonValue]
    status: str
    stage: str
    scope: str
    local_coverage: dict[str, JsonValue]
    rejection_reasons: tuple[str, ...]
    preparation_constraints: tuple[JsonValue, ...]
    choices: tuple[FamilyReportChoice, ...]


class RecoveryLocalChoice(HopModel):
    realization_id: str
    loop_nt: int
    loop_side_paired_bp: int
    selected: bool


class FamilyRecoveryProjection(HopModel):
    source_member: str
    target_member: str
    kind: str
    prior_status: str
    preferred_loop_nt: int | None
    foldback_choices: tuple[RecoveryLocalChoice, ...]
    basal_choice_count: int | None


class ConstructionFamilyReportProjection(HopModel):
    schema_id: Literal["hop.construction-family-report/v3"] = Field(
        default="hop.construction-family-report/v3", alias="schema"
    )
    family_id: str
    source_manifest_digest: str
    recorded_producer: dict[str, JsonValue]
    report_producer: dict[str, JsonValue]
    shared_properties: tuple[str, ...]
    upper_bounds: dict[str, int]
    members: tuple[FamilyReportMember, ...]
    selected_members: tuple[str, ...]
    selection_set_id: str | None
    baseline: str | None
    interpretation: str
    comparisons: tuple[FamilyReportComparison, ...] = ()
    authored_edits: tuple[FamilyReportEdit, ...] = ()
    revision: dict[str, JsonValue] | None = None
    family_controls: tuple[ComparisonControl, ...] = ()
    selected_controls: tuple[ComparisonControl, ...] = ()
    recovery: FamilyRecoveryProjection | None = None
    compared_properties: tuple[str, ...] = ()
