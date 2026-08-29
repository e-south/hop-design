"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/reactions.py

Defines exact molecular inputs, enzyme bindings, and concurrent reaction stages.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from itertools import pairwise

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.physical import SiteOrientation
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence


class ReactionMolecule(HopModel):
    """One exact reference strand and optional antiparallel complement in a state."""

    molecule_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    reference_sequence_5prime: str
    complement_sequence_5prime: str | None

    @field_validator("reference_sequence_5prime", "complement_sequence_5prime", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_aligned_length(self) -> ReactionMolecule:
        if self.complement_sequence_5prime is not None and len(
            self.complement_sequence_5prime
        ) != len(self.reference_sequence_5prime):
            raise ValueError("Aligned reaction-molecule strands must have equal lengths.")
        return self


class ReactionState(HopModel):
    """The complete set of molecules physically present before one stage."""

    state_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    molecules: tuple[ReactionMolecule, ...]

    @model_validator(mode="after")
    def validate_unique_molecules(self) -> ReactionState:
        molecule_ids = tuple(molecule.molecule_id for molecule in self.molecules)
        if len(molecule_ids) != len(set(molecule_ids)):
            raise ValueError("Reaction-state molecule ids must be unique.")
        return self

    def by_id(self, molecule_id: str) -> ReactionMolecule:
        """Resolve one molecule that is physically present in this state."""
        for molecule in self.molecules:
            if molecule.molecule_id == molecule_id:
                return molecule
        raise KeyError(molecule_id)


class DeclaredEnzymeBinding(HopModel):
    """One intended recognition span and its distinct operative cuts."""

    recognition_span: Span
    orientation: SiteOrientation
    reference_cut: Boundary | None
    complement_cut: Boundary | None

    @model_validator(mode="after")
    def validate_cuts(self) -> DeclaredEnzymeBinding:
        if self.reference_cut is None and self.complement_cut is None:
            raise ValueError("An enzyme binding must contain at least one operative cut.")
        return self


class ReactionOperation(HopModel):
    """One declared enzyme action within a reaction stage."""

    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    enzyme_id: ReferenceId
    role: EnzymeRole
    molecule_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    intended_binding: DeclaredEnzymeBinding


class ReactionStage(HopModel):
    """Concurrent enzyme operations resolved against one named pre-stage state."""

    stage_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    pre_state_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    post_state_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    operations: tuple[ReactionOperation, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_operations(self) -> ReactionStage:
        operation_ids = tuple(operation.operation_id for operation in self.operations)
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError("Reaction-stage operation ids must be unique.")
        if self.pre_state_id == self.post_state_id:
            raise ValueError("Reaction-stage pre-state and post-state ids must differ.")
        return self


class ReactionProgram(HopModel):
    """Ordered stages connected by the exact molecular states they transform."""

    program_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    states: tuple[ReactionState, ...] = Field(min_length=2)
    stages: tuple[ReactionStage, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_stage_order(self) -> ReactionProgram:
        state_ids = tuple(state.state_id for state in self.states)
        stage_ids = tuple(stage.stage_id for stage in self.stages)
        if len(state_ids) != len(set(state_ids)):
            raise ValueError("Reaction-program state ids must be unique.")
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("Reaction-program stage ids must be unique.")
        if len(self.stages) != len(self.states) - 1:
            raise ValueError("Reaction stages must connect consecutive states exactly once.")
        expected_connections = tuple(pairwise(state_ids))
        observed_connections = tuple(
            (stage.pre_state_id, stage.post_state_id) for stage in self.stages
        )
        if observed_connections != expected_connections:
            raise ValueError("Reaction stages must connect consecutive states in order.")
        return self


class ActionableEnzymeBinding(HopModel):
    """One physically actionable recognition and cut geometry in a reaction state."""

    enzyme_id: ReferenceId
    molecule_id: str
    recognition_span: Span
    orientation: SiteOrientation
    reference_cut: Boundary | None
    complement_cut: Boundary | None
    operation_id: str | None = None

    @model_validator(mode="after")
    def validate_cuts(self) -> ActionableEnzymeBinding:
        if self.reference_cut is None and self.complement_cut is None:
            raise ValueError("An actionable binding must contain at least one operative cut.")
        return self


class ReactionStageAssessment(HopModel):
    """State-aware intended, unintended, and concurrent-cut assessment."""

    stage_id: str
    resolved_against_state_id: str
    intended_bindings: tuple[ActionableEnzymeBinding, ...]
    undeclared_bindings: tuple[ActionableEnzymeBinding, ...]
    report: CheckReport


__all__ = [
    "ActionableEnzymeBinding",
    "DeclaredEnzymeBinding",
    "ReactionMolecule",
    "ReactionOperation",
    "ReactionProgram",
    "ReactionStage",
    "ReactionStageAssessment",
    "ReactionState",
]
