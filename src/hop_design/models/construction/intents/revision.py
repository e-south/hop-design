"""A small explicit permission change; experimental requirements remain authored."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import CharacterizedEnzyme

from ..discovery.placement import EndPlacement
from ..variants.envelope import ENVELOPE_FIELDS
from ..variants.parameters import ParameterSelection, validate_selections
from .request import ConstructionMethodChoices

CONTEXT_PARAMETER_FIELDS = {
    field.axis: field
    for field in ENVELOPE_FIELDS
    if field.axis
    and field.path.startswith("product.")
    and ".geometry." in field.path
    and field.kind in {"integers", "words", "choice"}
}
# One exact product uses one minimum; discovery permits a domain of minima.
# Reuse the same parameter vocabulary while routing to the survey's field.
CONTEXT_PARAMETER_FIELDS["adapter_annealing_min_nt"] = next(
    field for field in ENVELOPE_FIELDS if field.axis == "adapter_annealing_min_nt"
).model_copy(
    update={
        "path": "product.basal.annealing_lengths_nt",
        "kind": "integers",
        "label": "Permitted minimum adapter annealing (nt)",
    }
)


class RetainedConstructionLimits(HopModel):
    foldback: int | None = Field(default=None, ge=1)
    basal: int | None = Field(default=None, ge=1)


class DesignPermissionRevision(HopModel):
    schema_id: Literal["hop.design-permission-revision/v1"] = Field(
        default="hop.design-permission-revision/v1", alias="schema"
    )
    parameters: tuple[ParameterSelection, ...] = Field(default=(), max_length=16)
    methods: ConstructionMethodChoices = ConstructionMethodChoices()
    end_placements: tuple[EndPlacement, ...] | None = Field(
        default=None, min_length=1, max_length=64
    )
    add_enzymes: tuple[CharacterizedEnzyme, ...] = Field(default=(), max_length=16)
    retained_limits_nt: RetainedConstructionLimits = RetainedConstructionLimits()

    @model_validator(mode="after")
    def explicit_edits(self) -> "DesignPermissionRevision":
        validate_selections(self.parameters)
        normalized = [
            "foldback_arm_bp" if p.key == "loop_side_paired_bp" else p.key for p in self.parameters
        ]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Equivalent measurements cannot receive separate permission edits.")
        for parameter, key in zip(self.parameters, normalized, strict=True):
            if key not in CONTEXT_PARAMETER_FIELDS:
                raise ValueError(f"Parameter {key!r} has no independent context permission edit.")
            if parameter.values is None:
                assert parameter.maximum is not None and parameter.minimum is not None
                if parameter.maximum - parameter.minimum >= 256:
                    raise ValueError("A compact permission revision may expand at most 256 values.")
        if len({e.enzyme_id for e in self.add_enzymes}) != len(self.add_enzymes):
            raise ValueError("Added enzyme characterizations must have distinct identities.")
        if not (
            self.parameters
            or self.end_placements
            or self.add_enzymes
            or any(self.methods.model_dump().values())
            or any(self.retained_limits_nt.model_dump().values())
        ):
            raise ValueError("A permission revision must declare at least one change.")
        return self
