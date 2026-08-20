"""Strict contracts for foldback-junction evaluation and bounded search."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport
from hop_design.models.junction import FoldbackJunction, JunctionPairKind
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence


def _normalize_optional_exact_dna(value: object) -> str:
    if not isinstance(value, str):
        raise SequenceValidationError("DNA sequence must be a string.")
    if not value or value.isspace():
        return ""
    return normalize_dna_sequence(value, allow_degenerate=False)


class FoldbackConstraints(HopModel):
    """Caller-authored feasibility limits for one foldback junction."""

    max_mismatches: int = Field(ge=0)
    terminal_paired_bp_min: int = Field(ge=0)
    terminal_paired_bp_max: int = Field(ge=0)
    max_uninterrupted_paired_bp: int = Field(ge=0)
    max_added_nt: int = Field(ge=0)
    required_turn_nt: int = Field(ge=0)
    allow_protected_region_mismatches: bool

    @model_validator(mode="after")
    def validate_ranges(self) -> FoldbackConstraints:
        if self.terminal_paired_bp_max < self.terminal_paired_bp_min:
            raise ValueError(
                "terminal_paired_bp_max must be greater than or equal to terminal_paired_bp_min."
            )
        return self


class FoldbackEvaluationRequest(HopModel):
    """One explicit precursor, nick, turn, arm, and constraint request."""

    precursor_sequence: str
    nick_boundary: Boundary
    retained_tract_span: Span
    protected_region: Span
    turn_extension: str
    foldback_arm: str
    constraints: FoldbackConstraints

    @field_validator("precursor_sequence", "foldback_arm", mode="before")
    @classmethod
    def normalize_required_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @field_validator("turn_extension", mode="before")
    @classmethod
    def normalize_turn_extension(cls, value: object) -> str:
        return _normalize_optional_exact_dna(value)

    @model_validator(mode="after")
    def validate_coordinates(self) -> FoldbackEvaluationRequest:
        precursor_nt = len(self.precursor_sequence)
        if self.nick_boundary.offset > precursor_nt:
            raise ValueError("nick_boundary must stay inside the precursor sequence.")
        for label, span in (
            ("retained_tract_span", self.retained_tract_span),
            ("protected_region", self.protected_region),
        ):
            if span.end.offset > precursor_nt:
                raise ValueError(f"{label} must stay inside the precursor sequence.")
        if self.retained_tract_span.length.value != len(self.foldback_arm):
            raise ValueError("foldback_arm length must equal retained_tract_span length.")
        return self


class FoldbackSearchRequest(HopModel):
    """Foldback request whose arm is to be deterministically enumerated."""

    precursor_sequence: str
    nick_boundary: Boundary
    retained_tract_span: Span
    protected_region: Span
    turn_extension: str
    constraints: FoldbackConstraints

    @field_validator("precursor_sequence", mode="before")
    @classmethod
    def normalize_precursor(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @field_validator("turn_extension", mode="before")
    @classmethod
    def normalize_turn_extension(cls, value: object) -> str:
        return _normalize_optional_exact_dna(value)

    @model_validator(mode="after")
    def validate_coordinates(self) -> FoldbackSearchRequest:
        precursor_nt = len(self.precursor_sequence)
        if self.nick_boundary.offset > precursor_nt:
            raise ValueError("nick_boundary must stay inside the precursor sequence.")
        for label, span in (
            ("retained_tract_span", self.retained_tract_span),
            ("protected_region", self.protected_region),
        ):
            if span.end.offset > precursor_nt:
                raise ValueError(f"{label} must stay inside the precursor sequence.")
        if self.retained_tract_span.length.value == 0:
            raise ValueError("retained_tract_span must contain at least one nucleotide.")
        return self


class FoldbackEvaluation(HopModel):
    """Derived geometry, pairing measurements, and feasibility diagnostics."""

    precursor_sequence: str
    nick_boundary: Boundary
    retained_tract_span: Span
    protected_region: Span
    turn_extension: str
    designed_sequence: str
    junction: FoldbackJunction
    source_turn_sequence: str
    effective_turn_sequence: str
    foldback_arm: str
    mismatch_positions: tuple[int, ...]
    terminal_paired_bp: int = Field(ge=0)
    max_uninterrupted_paired_bp: int = Field(ge=0)
    added_nt: int = Field(ge=0)
    report: CheckReport

    @field_validator("precursor_sequence", "designed_sequence", "foldback_arm", mode="before")
    @classmethod
    def normalize_required_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @field_validator(
        "turn_extension",
        "source_turn_sequence",
        "effective_turn_sequence",
        mode="before",
    )
    @classmethod
    def normalize_optional_sequence(cls, value: object) -> str:
        return _normalize_optional_exact_dna(value)

    @property
    def junction_sequence(self) -> str:
        """Return the canonical junction sequence."""
        return self.junction.sequence

    @model_validator(mode="after")
    def validate_junction_projection(self) -> FoldbackEvaluation:
        precursor_nt = len(self.precursor_sequence)
        if self.nick_boundary.offset > precursor_nt:
            raise ValueError("Foldback nick boundary must stay inside the precursor sequence.")
        for label, span in (
            ("retained tract", self.retained_tract_span),
            ("protected region", self.protected_region),
        ):
            if span.end.offset > precursor_nt:
                raise ValueError(f"Foldback {label} must stay inside the precursor sequence.")
        retained = self.precursor_sequence[
            self.retained_tract_span.start.offset : self.retained_tract_span.end.offset
        ]
        expected_source_turn = self.precursor_sequence[self.retained_tract_span.end.offset :]
        expected_effective_turn = f"{expected_source_turn}{self.turn_extension}"
        expected_junction = f"{retained}{expected_effective_turn}{self.foldback_arm}"
        expected_designed = f"{self.precursor_sequence}{self.turn_extension}{self.foldback_arm}"
        if self.source_turn_sequence != expected_source_turn:
            raise ValueError("Foldback source turn must derive from the precursor sequence.")
        if self.effective_turn_sequence != expected_effective_turn:
            raise ValueError("Foldback effective turn must derive from source turn and extension.")
        if self.junction.sequence != expected_junction:
            raise ValueError("Foldback junction sequence must derive from precursor geometry.")
        if self.designed_sequence != expected_designed:
            raise ValueError("Foldback designed sequence must derive from its authored inputs.")
        if self.added_nt != len(self.turn_extension) + len(self.foldback_arm):
            raise ValueError("Foldback added-nt count must match extension and arm lengths.")
        if self.junction.retained_tract_span.length.value != self.retained_tract_span.length.value:
            raise ValueError("Foldback junction retained tract must match precursor geometry.")
        if self.junction.turn_span.length.value != len(self.effective_turn_sequence):
            raise ValueError("Foldback junction turn span must match the effective turn.")
        observed_mismatches = tuple(
            position
            for position, pair in enumerate(self.junction.pairs)
            if pair.kind is not JunctionPairKind.WATSON_CRICK
        )
        if observed_mismatches != self.mismatch_positions:
            raise ValueError("Foldback mismatch positions must match canonical junction pairs.")
        if self.junction.foldback_arm_span.length.value != len(self.foldback_arm):
            raise ValueError("Foldback evaluation arm must match its canonical junction.")
        matched_mask = tuple(
            pair.kind is JunctionPairKind.WATSON_CRICK for pair in self.junction.pairs
        )
        terminal_paired_bp = 0
        for matched in matched_mask:
            if not matched:
                break
            terminal_paired_bp += 1
        max_uninterrupted_paired_bp = 0
        current_run = 0
        for matched in matched_mask:
            current_run = current_run + 1 if matched else 0
            max_uninterrupted_paired_bp = max(max_uninterrupted_paired_bp, current_run)
        if self.terminal_paired_bp != terminal_paired_bp:
            raise ValueError("Foldback terminal paired run must match canonical junction pairs.")
        if self.max_uninterrupted_paired_bp != max_uninterrupted_paired_bp:
            raise ValueError("Foldback longest paired run must match canonical junction pairs.")
        has_nick_geometry_diagnostic = any(
            diagnostic.code == "HOP-FOLD-001" for diagnostic in self.report.diagnostics
        )
        nick_geometry_is_invalid = self.retained_tract_span.start != self.nick_boundary
        if has_nick_geometry_diagnostic != nick_geometry_is_invalid:
            raise ValueError("Foldback report must agree with HOP-FOLD-001 nick geometry.")
        return self


class FoldbackSearchLimits(HopModel):
    """Hard budgets for foldback enumeration."""

    max_search_nodes: int = Field(ge=1)
    max_hits: int = Field(ge=1)


class FoldbackSearchResult(HopModel):
    """A bounded search result that makes incomplete exploration explicit."""

    status: Literal["complete", "infeasible", "truncated"]
    hits: tuple[FoldbackEvaluation, ...]
    candidate_space_size: int = Field(ge=1)
    search_nodes_examined: int = Field(ge=0)
    truncated_by: Literal["max_search_nodes", "max_hits"] | None = None

    @model_validator(mode="after")
    def validate_status(self) -> FoldbackSearchResult:
        if (self.status == "truncated") != (self.truncated_by is not None):
            raise ValueError("truncated status and truncated_by must be declared together.")
        if self.status == "infeasible" and self.hits:
            raise ValueError("An infeasible search cannot contain hits.")
        if self.status == "infeasible" and self.search_nodes_examined != self.candidate_space_size:
            raise ValueError("An infeasible search must examine the full candidate space.")
        if self.status == "complete" and not self.hits:
            raise ValueError("A complete search must contain at least one feasible hit.")
        if self.status == "complete" and self.search_nodes_examined != self.candidate_space_size:
            raise ValueError("A complete search must examine the full candidate space.")
        if self.hits and self.search_nodes_examined == 0:
            raise ValueError("A search cannot contain hits without examining candidates.")
        if self.search_nodes_examined > self.candidate_space_size:
            raise ValueError("search_nodes_examined cannot exceed candidate_space_size.")
        if self.status == "truncated" and self.search_nodes_examined >= self.candidate_space_size:
            raise ValueError("A truncated search must stop before the candidate space is complete.")
        if self.truncated_by == "max_hits" and not self.hits:
            raise ValueError("A max-hits truncation must contain at least one hit.")
        return self


__all__ = [
    "FoldbackConstraints",
    "FoldbackEvaluation",
    "FoldbackEvaluationRequest",
    "FoldbackSearchLimits",
    "FoldbackSearchRequest",
    "FoldbackSearchResult",
]
