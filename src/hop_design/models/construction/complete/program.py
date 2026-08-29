"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/program.py

Defines exact full-route chronology around assessed enzyme-phase programs.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from itertools import pairwise
from typing import Any, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import _content_id
from hop_design.models.molecular_state import MolecularStrand, StrandPairObservation
from hop_design.models.reactions import ReactionProgram, ReactionStageAssessment

from .associations import ConstructionBondState
from .state import ConstructionState, ConstructionStatePhase
from .transition_replay import validate_non_enzyme_transition


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
        elif (
            self.reaction_program_id is not None
            or self.reaction_boundary_mapping is not None
            or self.exact_relation is None
        ):
            raise ValueError("A non-enzyme transition requires only an exact state relation.")
        if self.exact_relation is not None and (
            self.exact_relation.pre_state_id != self.pre_state_id
            or self.exact_relation.post_state_id != self.post_state_id
        ):
            raise ValueError("Exact state relation must bind the transition boundaries.")
        return self


class ConstructionProgram(HopModel):
    """Contiguous full-route chronology with embedded assessed enzyme phases."""

    program_id: str = Field(pattern=r"^hop:construction-program/[0-9a-f]{64}@1$")
    states: tuple[ConstructionState, ...] = Field(min_length=2)
    transitions: tuple[ConstructionTransition, ...] = Field(min_length=1)
    reaction_programs: tuple[ReactionProgram, ...]
    stage_assessments: tuple[ReactionStageAssessment, ...]

    @classmethod
    def create(cls, **content: object) -> ConstructionProgram:
        draft = cls.model_construct(program_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"program_id"})
        return cls.model_validate(
            {"program_id": _content_id("construction-program", 1, seed), **content}
        )

    @model_validator(mode="after")
    def validate_program(self) -> ConstructionProgram:
        content = self.model_dump(mode="json", exclude={"program_id"})
        if self.program_id != _content_id("construction-program", 1, content):
            raise ValueError("Construction-program identity must seal its full chronology.")
        state_ids = tuple(item.state_id for item in self.states)
        if len(state_ids) != len(set(state_ids)):
            raise ValueError("Construction-program state identities must be unique.")
        if len(self.transitions) != len(self.states) - 1:
            raise ValueError("Construction transitions must connect consecutive states exactly.")
        expected = tuple(pairwise(state_ids))
        observed = tuple((item.pre_state_id, item.post_state_id) for item in self.transitions)
        if observed != expected:
            raise ValueError("Construction transitions must connect consecutive states in order.")
        if any(item.phase is ConstructionStatePhase.UNSPECIFIED for item in self.states):
            raise ValueError("Complete construction programs require fully typed phases.")
        programs = {item.program_id: item for item in self.reaction_programs}
        if len(programs) != len(self.reaction_programs):
            raise ValueError("Embedded ReactionProgram ids must be unique.")
        referenced = tuple(
            item.reaction_program_id
            for item in self.transitions
            if item.reaction_program_id is not None
        )
        if set(referenced) != set(programs) or len(referenced) != len(set(referenced)):
            raise ValueError("Every enzyme-phase program must be referenced exactly once.")
        states_by_id = {item.state_id: item for item in self.states}
        expected_phases = {
            ConstructionTransitionKind.ENZYME_PHASE: (
                ConstructionStatePhase.DUPLEX,
                ConstructionStatePhase.CLEAVED_DUPLEX,
            ),
            ConstructionTransitionKind.DENATURATION: (
                ConstructionStatePhase.CLEAVED_DUPLEX,
                ConstructionStatePhase.DENATURED_FRAGMENTS,
            ),
            ConstructionTransitionKind.FRAGMENT_SELECTION: (
                ConstructionStatePhase.DENATURED_FRAGMENTS,
                ConstructionStatePhase.SELECTED_FRAGMENTS,
            ),
            ConstructionTransitionKind.ANNEALING: (
                ConstructionStatePhase.SELECTED_FRAGMENTS,
                ConstructionStatePhase.ANNEALED_COMPLEX,
            ),
            ConstructionTransitionKind.LIGATION: (
                ConstructionStatePhase.ANNEALED_COMPLEX,
                ConstructionStatePhase.LIGATED_PRODUCT,
            ),
        }
        for transition in self.transitions:
            pre_state = states_by_id[transition.pre_state_id]
            post_state = states_by_id[transition.post_state_id]
            phases = expected_phases.get(transition.kind)
            if (
                phases is not None
                and ConstructionStatePhase.UNSPECIFIED not in {pre_state.phase, post_state.phase}
                and (pre_state.phase, post_state.phase) != phases
            ):
                raise ValueError("Construction transition must preserve physical phase order.")
            if transition.reaction_program_id is None:
                validate_non_enzyme_transition(
                    kind=transition.kind.value,
                    pre_state=pre_state,
                    post_state=post_state,
                )
                continue
            program = programs[transition.reaction_program_id]
            mapping = transition.reaction_boundary_mapping
            if mapping is None:
                raise ValueError("Enzyme-phase transition lacks its exact boundary mapping.")
            if mapping.pre_strands != pre_state.molecules or mapping.post_strands != (
                post_state.molecules
            ):
                raise ValueError(
                    "Reaction-boundary mapping must preserve exact construction strands."
                )
            if (
                mapping.pre_pairings != pre_state.pairings
                or mapping.post_pairings != post_state.pairings
                or mapping.pre_bonds != pre_state.formed_bonds
                or mapping.post_bonds != post_state.formed_bonds
            ):
                raise ValueError(
                    "Reaction-boundary mapping must preserve exact molecular associations."
                )
            expected_pre = self._reaction_sequences(program.states[0])
            expected_post = self._reaction_sequences(program.states[-1])
            observed_pre = tuple(item.sequence for item in pre_state.molecules)
            observed_post = tuple(item.sequence for item in post_state.molecules)
            if observed_pre != expected_pre or observed_post != expected_post:
                raise ValueError(
                    "Enzyme-phase states must equal the referenced ReactionProgram boundaries."
                )
        stage_ids = tuple(
            stage.stage_id for item in self.reaction_programs for stage in item.stages
        )
        if tuple(item.stage_id for item in self.stage_assessments) != stage_ids:
            raise ValueError("Stage assessments must cover all embedded enzyme phases in order.")
        stages = tuple(stage for item in self.reaction_programs for stage in item.stages)
        for stage, assessment in zip(stages, self.stage_assessments, strict=True):
            if assessment.resolved_against_state_id != stage.pre_state_id:
                raise ValueError("Stage assessment must bind its exact enzyme-phase pre-state.")
            operations = {item.operation_id: item for item in stage.operations}
            if (
                tuple(item.operation_id for item in assessment.intended_bindings)
                != tuple(operations)
                or assessment.undeclared_bindings
            ):
                raise ValueError("Stage assessment must cover the exact declared operations.")
            for binding in assessment.intended_bindings:
                operation_id = binding.operation_id
                if operation_id is None:
                    raise ValueError(
                        "Stage assessment evidence must replay its declared operation."
                    )
                operation = operations[operation_id]
                if (
                    binding.enzyme_id != operation.enzyme_id
                    or binding.molecule_id != operation.molecule_id
                    or binding.recognition_span != operation.intended_binding.recognition_span
                    or binding.orientation is not operation.intended_binding.orientation
                    or binding.reference_cut != operation.intended_binding.reference_cut
                    or binding.complement_cut != operation.intended_binding.complement_cut
                ):
                    raise ValueError(
                        "Stage assessment evidence must replay its declared operation."
                    )
        if any(item.report.has_errors for item in self.stage_assessments):
            raise ValueError("A complete construction program cannot contain rejected stages.")
        return self

    @staticmethod
    def _reaction_sequences(state: object) -> tuple[str, ...]:
        molecules = cast(Any, state).molecules
        return tuple(
            sequence
            for molecule in molecules
            for sequence in (
                molecule.reference_sequence_5prime,
                molecule.complement_sequence_5prime,
            )
            if sequence is not None
        )


__all__ = [
    "ConstructionProgram",
    "ConstructionState",
    "ConstructionStatePhase",
    "ConstructionTransition",
    "ConstructionTransitionKind",
    "ExactStateRelation",
    "ReactionBoundaryMapping",
]
