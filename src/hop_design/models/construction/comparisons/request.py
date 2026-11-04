"""Declare a comparison separately from permission to search a scaffold envelope."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.family.request import ScaffoldDimension, SharedProperty
from hop_design.models.construction.stage_controls import ResolvedStageControl, StageControl
from hop_design.models.sequence import normalize_dna_sequence

from .materials import MaterialRole, PriorMaterialReuse, SelectedPreparationReference


class RequiredComparisonMember(HopModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,31}$")
    dimensions: dict[ScaffoldDimension, Annotated[int, Field(ge=0)]] = Field(default_factory=dict)
    release_enzyme_id: str | None = None

    @model_validator(mode="after")
    def require_selector(self) -> RequiredComparisonMember:
        if not self.dimensions and self.release_enzyme_id is None:
            raise ValueError("A required member needs a molecular dimension or method selector.")
        return self


class ComparisonDeclarations(HopModel):
    discovery: ScaffoldDiscoveryRequest
    required_members: tuple[RequiredComparisonMember, ...] = Field(max_length=64)
    shared_properties: tuple[SharedProperty, ...]
    preserve_material_roles: tuple[MaterialRole, ...]
    max_group_evaluations: int = Field(ge=1, le=100_000)
    max_sets: int = Field(default=64, ge=1, le=256)

    @property
    def comparison_stage(self) -> str:
        return self.discovery.comparison_stage

    @model_validator(mode="after")
    def unique_declarations(self) -> ComparisonDeclarations:
        names = [m.name for m in self.required_members]
        if len(names) != len(set(names)):
            raise ValueError("Required comparison member names must be unique.")
        for name in ("shared_properties", "preserve_material_roles"):
            value = getattr(self, name)
            if len(value) != len(set(value)):
                raise ValueError(f"{name} must not repeat.")
        return self


class ComparisonBrief(ComparisonDeclarations):
    schema_id: Literal["hop.comparison-brief/v1"] = Field(alias="schema")
    purpose: Literal["distinct_substrates", "preparation_alternatives"]


class ComparisonProductReference(SelectedPreparationReference):
    stage: Literal["hairpin", "endpoint"]


class SequenceComparisonMember(RequiredComparisonMember):
    loop_sequence: str | None = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator("loop_sequence")
    @classmethod
    def exact_loop(cls, value: str | None) -> str | None:
        return None if value is None else normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def require_selector(self) -> SequenceComparisonMember:
        if not self.dimensions and self.release_enzyme_id is None and self.loop_sequence is None:
            raise ValueError("A required member needs a molecular dimension, sequence or method.")
        if self.loop_sequence is not None and (
            "loop_nt" in self.dimensions and self.dimensions["loop_nt"] != len(self.loop_sequence)
        ):
            raise ValueError("Required loop sequence and dimension must have the same length.")
        return self


class ComparisonGroup(HopModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,31}$")
    members: tuple[str, ...] = Field(min_length=1, max_length=64)
    product_relationship: Literal["identical"]
    product_reference: ComparisonProductReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


def validate_partition(
    groups: tuple[ComparisonGroup, ...],
    required_members: tuple[RequiredComparisonMember, ...],
    stage: str,
) -> None:
    names = [g.name for g in groups]
    members = [name for g in groups for name in g.members]
    if len(names) != len(set(names)):
        raise ValueError("Comparison group names must be unique.")
    if len(members) != len(set(members)):
        raise ValueError("Comparison groups must not overlap or repeat members.")
    if set(members) != {m.name for m in required_members}:
        raise ValueError("Comparison groups must contain every required member exactly once.")
    if any(g.product_reference is not None and g.product_reference.stage != stage for g in groups):
        raise ValueError("Product reference stage must match the declared comparison stage.")


class ComparisonRequirements(HopModel):
    """Shared member and control declarations, independent of the admitted source."""

    required_members: tuple[SequenceComparisonMember, ...] = Field(min_length=1, max_length=64)
    purpose: Literal["distinct_substrates", "preparation_alternatives", "grouped_substrates"] = (
        "distinct_substrates"
    )
    shared_properties: tuple[SharedProperty, ...] = ()
    preserve_material_roles: tuple[MaterialRole, ...] = ()
    stage_controls: tuple[StageControl, ...] = Field(default=(), max_length=192)
    groups: tuple[ComparisonGroup, ...] = Field(default=(), max_length=64)
    between_groups: Literal["distinct"] | None = None
    max_group_evaluations: int = Field(ge=1, le=100_000)
    max_sets: int = Field(default=64, ge=1, le=256)

    @model_validator(mode="after")
    def unique_declarations(self) -> ComparisonRequirements:
        names = [m.name for m in self.required_members]
        if len(names) != len(set(names)):
            raise ValueError("Required comparison member names must be unique.")
        for name in ("shared_properties", "preserve_material_roles"):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must not repeat.")
        return self


class ComparisonAssessment(ComparisonRequirements):
    """Assess admitted molecules without fabricating a discovery request."""

    stage: Literal["hairpin", "endpoint"]

    @property
    def comparison_stage(self) -> str:
        return self.stage

    @model_validator(mode="after")
    def validate_scopes(self) -> ComparisonAssessment:
        validate_assessment_scopes(
            self.purpose,
            self.groups,
            self.between_groups,
            self.required_members,
            self.stage_controls,
            self.stage,
        )
        return self


class GroupedComparisonBrief(ComparisonDeclarations):
    schema_id: Literal["hop.comparison-brief/v2"] = Field(alias="schema")
    purpose: Literal["grouped_substrates"]
    required_members: tuple[SequenceComparisonMember, ...] = Field(max_length=64)
    groups: tuple[ComparisonGroup, ...] = Field(min_length=1, max_length=64)
    between_groups: Literal["distinct"]

    @model_validator(mode="after")
    def partition_members(self) -> GroupedComparisonBrief:
        validate_partition(self.groups, self.required_members, self.discovery.comparison_stage)
        return self


class StageComparisonBrief(ComparisonDeclarations):
    """Explicit stages and groups without changing the earlier shared-property contract."""

    schema_id: Literal["hop.comparison-brief/v3"] = Field(alias="schema")
    purpose: Literal["distinct_substrates", "preparation_alternatives", "grouped_substrates"]
    required_members: tuple[SequenceComparisonMember, ...] = Field(max_length=64)
    groups: tuple[ComparisonGroup, ...] = Field(default=(), max_length=64)
    between_groups: Literal["distinct"] | None = None
    stage_controls: tuple[StageControl, ...] = Field(default=(), max_length=192)
    reuse_prior_materials: PriorMaterialReuse | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def validate_scopes(self) -> StageComparisonBrief:
        validate_assessment_scopes(
            self.purpose,
            self.groups,
            self.between_groups,
            self.required_members,
            self.stage_controls,
            self.comparison_stage,
        )
        return self


def validate_assessment_scopes(
    purpose: str,
    groups: tuple[ComparisonGroup, ...],
    between_groups: str | None,
    required_members: tuple[SequenceComparisonMember, ...],
    stage_controls: tuple[StageControl, ...],
    stage: str,
) -> None:
    if purpose == "grouped_substrates":
        if not groups or between_groups != "distinct":
            raise ValueError("Grouped comparisons need groups and distinct between_groups.")
        validate_partition(groups, required_members, stage)
    elif groups or between_groups is not None:
        raise ValueError("Groups and between_groups require grouped_substrates purpose.")
    names = {group.name for group in groups}
    keys = [(c.property, c.stage, c.scope, c.group) for c in stage_controls]
    if len(keys) != len(set(keys)):
        raise ValueError("Stage controls must not repeat.")
    if any(c.group is not None and c.group not in names for c in stage_controls):
        raise ValueError("Stage control names an unknown comparison group.")


type ComparisonRequest = ComparisonBrief | GroupedComparisonBrief | StageComparisonBrief
type ComparisonAssessmentRequest = ComparisonRequest | ComparisonAssessment


def resolved_stage_controls(brief: ComparisonAssessmentRequest) -> tuple[ResolvedStageControl, ...]:
    if not isinstance(brief, (StageComparisonBrief, ComparisonAssessment)):
        return ()
    groups = {g.name: g.members for g in brief.groups}
    return tuple(
        ResolvedStageControl(
            property=control.property,
            stage=control.stage,
            scope=control.scope,
            group=control.group,
            members=tuple(
                sorted(
                    groups[control.group]
                    if control.group is not None
                    else [m.name for m in brief.required_members]
                )
            ),
        )
        for control in brief.stage_controls
    )
