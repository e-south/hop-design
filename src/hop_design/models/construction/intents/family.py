"""Explicit finite experimental membership with ordinary optional design requirements."""

from typing import Any, Literal, Self

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import normalize_dna_sequence

from ..comparisons.materials import MaterialRole
from ..family.request import SharedProperty
from ..molecular.sequence_family import family_cardinality
from .request import ConstructionIntentRequirements


class ConstructionFamilyIntent(ConstructionIntentRequirements):
    schema_id: Literal["hop.construction-family-intent/v1"] = Field(alias="schema")
    stem_arm: str
    max_members: int = Field(ge=1, le=64)
    max_total_evaluations: int = Field(ge=1, le=1024)
    shared_properties: tuple[SharedProperty, ...] = ()
    shared_material_roles: tuple[MaterialRole, ...] = ()

    @field_validator("stem_arm")
    @classmethod
    def symbolic_stem(cls, value: str) -> str:
        return normalize_dna_sequence(value, allow_degenerate=True)

    @model_validator(mode="after")
    def bounded_membership(self) -> Self:
        count = family_cardinality(self.stem_arm, self.max_members)
        if count > self.max_total_evaluations:
            raise ValueError("Required members exceed max_total_evaluations.")
        for values in (self.shared_properties, self.shared_material_roles):
            if len(set(values)) != len(values):
                raise ValueError("Shared properties and material roles must not repeat.")
        if count > 1 and "stem_sequence" in self.shared_properties:
            raise ValueError("Different required stems cannot share stem_sequence.")
        return self

    def exact_intent(self, stem: str) -> dict[str, Any]:
        return {
            **self.model_dump(
                mode="json",
                by_alias=True,
                exclude={
                    "schema_id",
                    "max_members",
                    "max_total_evaluations",
                    "shared_properties",
                    "shared_material_roles",
                },
            ),
            "schema": "hop.construction-intent/v1",
            "stem_arm": stem,
        }


class DesignFamilySelection(HopModel):
    schema_id: Literal["hop.design-family-selection/v1"] = Field(alias="schema")
    request_digest: str
    members: dict[str, dict[str, Any]]
    baseline: str
    selection_digest: str
