"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/transition.py

Defines exact authorities for transitions between complete-construction states.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import _content_id
from hop_design.models.molecular_state import MolecularStrand, StrandPairObservation

from .associations import ConstructionBondState
from .pcr import PcrTransitionAuthority


class ExactStateRelation(HopModel):
    """Content identity binding one exact derived state to its exact precursor state."""

    relation_id: str = Field(pattern=r"^hop:state-relation/[0-9a-f]{64}@1$")
    pre_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    post_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")

    @classmethod
    def create(cls, *, pre_state_id: str, post_state_id: str) -> ExactStateRelation:
        content = {"pre_state_id": pre_state_id, "post_state_id": post_state_id}
        return cls(
            relation_id=_content_id("state-relation", 1, content),
            pre_state_id=pre_state_id,
            post_state_id=post_state_id,
        )

    @model_validator(mode="after")
    def validate_identity(self) -> ExactStateRelation:
        expected = _content_id(
            "state-relation",
            1,
            {"pre_state_id": self.pre_state_id, "post_state_id": self.post_state_id},
        )
        if self.relation_id != expected:
            raise ValueError("State-relation identity must seal both exact state identities.")
        if self.pre_state_id == self.post_state_id:
            raise ValueError("A derived-state relation must change the exact molecular state.")
        return self


class ReactionBoundaryMapping(HopModel):
    """Exact relation from one reaction phase boundary to construction strands."""

    mapping_id: str = Field(pattern=r"^hop:reaction-boundary-mapping/[0-9a-f]{64}@1$")
    reaction_program_id: str
    pre_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    post_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    pre_strands: tuple[MolecularStrand, ...] = Field(min_length=1)
    post_strands: tuple[MolecularStrand, ...] = Field(min_length=1)
    pre_pairings: tuple[StrandPairObservation, ...] = ()
    post_pairings: tuple[StrandPairObservation, ...] = ()
    pre_bonds: tuple[ConstructionBondState, ...] = ()
    post_bonds: tuple[ConstructionBondState, ...] = ()

    @classmethod
    def create(cls, **content: object) -> ReactionBoundaryMapping:
        draft = cls.model_construct(mapping_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"mapping_id"})
        return cls.model_validate(
            {"mapping_id": _content_id("reaction-boundary-mapping", 1, seed), **content}
        )

    @model_validator(mode="after")
    def validate_identity(self) -> ReactionBoundaryMapping:
        content = self.model_dump(mode="json", exclude={"mapping_id"})
        if self.mapping_id != _content_id("reaction-boundary-mapping", 1, content):
            raise ValueError("Reaction-boundary identity must seal exact mapped strands.")
        return self


class ConstructionTransitionKind(StrEnum):
    """Closed physical transition kinds in complete construction chronology."""

    ENZYME_PHASE = "enzyme_phase"
    DENATURATION = "denaturation"
    FRAGMENT_SELECTION = "fragment_selection"
    ANNEALING = "annealing"
    LIGATION = "ligation"
    PRIMER_EXTENSION = "primer_extension"
    END_GENERATION = "end_generation"


_ENZYME_KINDS = {
    ConstructionTransitionKind.ENZYME_PHASE,
    ConstructionTransitionKind.END_GENERATION,
}


class ConstructionTransition(HopModel):
    """One exact chronological transition with one authoritative evidence mode."""

    transition_id: str = Field(pattern=r"^hop:construction-transition/[0-9a-f]{64}@1$")
    kind: ConstructionTransitionKind
    pre_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    post_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    reaction_program_id: str | None = None
    reaction_boundary_mapping: ReactionBoundaryMapping | None = None
    exact_relation: ExactStateRelation | None = None
    pcr_authority: PcrTransitionAuthority | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @classmethod
    def create(cls, **content: object) -> ConstructionTransition:
        draft = cls.model_construct(transition_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"transition_id"})
        return cls.model_validate(
            {"transition_id": _content_id("construction-transition", 1, seed), **content}
        )

    @model_validator(mode="after")
    def validate_authority(self) -> ConstructionTransition:
        content = self.model_dump(mode="json", exclude={"transition_id"})
        if self.transition_id != _content_id("construction-transition", 1, content):
            raise ValueError("Construction-transition identity must seal its exact authority.")
        if self.kind in _ENZYME_KINDS:
            if (
                self.reaction_program_id is None
                or self.reaction_boundary_mapping is None
                or self.exact_relation is not None
                or self.pcr_authority is not None
            ):
                raise ValueError(
                    "An enzyme transition requires a ReactionProgram and exact boundary mapping."
                )
            mapping = self.reaction_boundary_mapping
            if (
                mapping.reaction_program_id != self.reaction_program_id
                or mapping.pre_state_id != self.pre_state_id
                or mapping.post_state_id != self.post_state_id
            ):
                raise ValueError("Reaction-boundary mapping must bind the transition authority.")
            if mapping.pre_strands == mapping.post_strands:
                raise ValueError("An enzyme phase must change the exact molecular state.")
        elif self.pcr_authority is None and (
            self.reaction_program_id is not None
            or self.reaction_boundary_mapping is not None
            or self.exact_relation is None
        ):
            raise ValueError("A non-enzyme transition requires only an exact state relation.")
        elif self.pcr_authority is not None and (
            self.reaction_program_id is not None
            or self.reaction_boundary_mapping is not None
            or self.exact_relation is not None
        ):
            raise ValueError("A PCR transition requires only its exact molecular authority.")
        if self.pcr_authority is not None and self.kind not in {
            ConstructionTransitionKind.DENATURATION,
            ConstructionTransitionKind.ANNEALING,
            ConstructionTransitionKind.LIGATION,
            ConstructionTransitionKind.PRIMER_EXTENSION,
        }:
            raise ValueError("PCR molecular authority must match a PCR transition kind.")
        if self.exact_relation is not None and (
            self.exact_relation.pre_state_id != self.pre_state_id
            or self.exact_relation.post_state_id != self.post_state_id
        ):
            raise ValueError("Exact state relation must bind the transition boundaries.")
        if self.pcr_authority is not None and (
            self.pcr_authority.pre_state_id != self.pre_state_id
            or self.pcr_authority.post_state_id != self.post_state_id
        ):
            raise ValueError("PCR molecular authority must bind transition state identities.")
        return self


__all__ = [
    "ConstructionTransition",
    "ConstructionTransitionKind",
    "ExactStateRelation",
    "ReactionBoundaryMapping",
]
