"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/targets.py

Defines payload-centered construction contracts and discovery evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.junction import Strand
from hop_design.models.references import ReferenceId


class NickStrandSelection(StrEnum):
    """Whether local discovery should search either exact nick strand."""

    ANY = "any"


class FoldbackTarget(HopModel):
    """Requested retained foldback geometry in final-payload coordinates."""

    family: Literal["foldback"] = "foldback"
    nick_strand: Strand | NickStrandSelection = NickStrandSelection.ANY
    junction_offset_nt: int = Field(ge=0)
    loop_length_nt: int = Field(ge=1)
    annealing_arm_length_bp: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_nick_offset(self) -> FoldbackTarget:
        if self.junction_offset_nt > self.annealing_arm_length_bp:
            raise ValueError("The foldback nick must lie within the first annealing arm.")
        return self


class BasalPairClass(StrEnum):
    """Construction bookkeeping for one basal source-adapter pair."""

    MATCH = "match"
    WOBBLE = "wobble"
    MISMATCH = "mismatch"


class BasalPairAllowance(StrEnum):
    """Authored allowed physical class for one basal pairing position."""

    MATCH = "match"
    WOBBLE = "wobble"
    MISMATCH = "mismatch"
    ANY = "any"


class BasalPairConstraint(HopModel):
    """One authored class constraint ordered from the payload outward."""

    position_from_ligation: int = Field(ge=0)
    allowed_class: BasalPairAllowance


class BasalTarget(HopModel):
    """Basal nick and adapter-pairing geometry through the PCR intermediate."""

    family: Literal["basal"] = "basal"
    nick_strand: Strand | NickStrandSelection
    nick_offset_nt: int = Field(ge=0)
    pairing_constraints: tuple[BasalPairConstraint, ...] = ()
    ligation_proximal_match_required: bool = False

    @model_validator(mode="after")
    def validate_pairing_constraints(self) -> BasalTarget:
        positions = tuple(item.position_from_ligation for item in self.pairing_constraints)
        if positions != tuple(range(len(positions))):
            raise ValueError("Basal pairing positions must be contiguous from the payload outward.")
        if (
            self.ligation_proximal_match_required
            and self.pairing_constraints
            and self.pairing_constraints[0].allowed_class is not BasalPairAllowance.MATCH
        ):
            raise ValueError("The payload-proximal basal pair must be a match.")
        return self


LocalGeometryTarget = Annotated[FoldbackTarget | BasalTarget, Field(discriminator="family")]


class ConstructionConstraints(HopModel):
    """Hard invariants shared by local construction discovery."""

    preserve_payload: Literal[True] = True
    forbid_unintended_actionable_sites: Literal[True] = True
    require_all_members_compatible: bool = False


class ConstructionPreferences(HopModel):
    """Non-authoritative ordering preferences over already valid realizations."""

    retained_construction: Literal["compact"] = "compact"
    payload_compatibility: Literal["report"] = "report"
    ranking: Literal["none"] = "none"
    preferred_enzyme_ids: tuple[ReferenceId, ...] = ()

    @field_validator("preferred_enzyme_ids", mode="after")
    @classmethod
    def canonicalize_preferred_enzymes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Preferred enzyme ids must be unique.")
        return tuple(sorted(values))
