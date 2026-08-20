"""Resolved foldback- and basal-junction contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import BasePairCount, Span
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import (
    SequenceValidationError,
    normalize_dna_sequence,
    reverse_complement_iupac,
)


class Strand(StrEnum):
    """A declared strand role in a duplex representation."""

    TOP = "top"
    BOTTOM = "bottom"


class JunctionPairKind(StrEnum):
    """Physical classification of one aligned nucleotide pair."""

    WATSON_CRICK = "watson_crick"
    GT_WOBBLE = "gt_wobble"
    HARD_MISMATCH = "hard_mismatch"


class JunctionPairObservation(HopModel):
    """One physical pair with literal bases and indexes on two aligned arms."""

    left_index: int = Field(ge=0)
    right_index: int = Field(ge=0)
    left_base: str
    right_base: str
    kind: JunctionPairKind

    @field_validator("left_base", "right_base", mode="before")
    @classmethod
    def normalize_base(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        normalized = normalize_dna_sequence(value, allow_degenerate=False)
        if len(normalized) != 1:
            raise ValueError("Junction pair bases must contain exactly one nucleotide.")
        return normalized

    @model_validator(mode="after")
    def validate_kind(self) -> JunctionPairObservation:
        aligned_right = reverse_complement_iupac(self.right_base)
        is_watson_crick = self.left_base == aligned_right
        is_gt = (self.left_base, self.right_base) in {("G", "T"), ("T", "G")}
        if self.kind is JunctionPairKind.WATSON_CRICK and not is_watson_crick:
            raise ValueError("Watson-Crick pair calls must match the literal bases.")
        if self.kind is JunctionPairKind.GT_WOBBLE and not is_gt:
            raise ValueError("G:T wobble pair calls must contain literal G and T bases.")
        if self.kind is JunctionPairKind.HARD_MISMATCH and is_watson_crick:
            raise ValueError("Hard-mismatch pair calls must not be Watson-Crick pairs.")
        return self

    @property
    def aligned_right_base(self) -> str:
        """Return the right base complemented into left-arm display orientation."""
        return reverse_complement_iupac(self.right_base)

    @property
    def is_match(self) -> bool:
        """Return whether this observation is Watson-Crick paired."""
        return self.kind is JunctionPairKind.WATSON_CRICK


class FoldbackJunction(HopModel):
    """The contiguous physical junction between payload and paired arms."""

    junction_id: ReferenceId
    sequence: str
    retained_tract_span: Span
    turn_span: Span
    foldback_arm_span: Span
    pairs: tuple[JunctionPairObservation, ...]

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_geometry(self) -> FoldbackJunction:
        spans = (self.retained_tract_span, self.turn_span, self.foldback_arm_span)
        boundaries = [
            spans[0].start.offset,
            spans[0].end.offset,
            spans[1].start.offset,
            spans[1].end.offset,
            spans[2].start.offset,
            spans[2].end.offset,
        ]
        expected = [
            0,
            spans[0].end.offset,
            spans[0].end.offset,
            spans[1].end.offset,
            spans[1].end.offset,
            len(self.sequence),
        ]
        if boundaries != expected:
            raise ValueError(
                "Retained tract, turn, and foldback arm must partition the junction sequence."
            )
        if self.retained_tract_span.length.value != self.foldback_arm_span.length.value:
            raise ValueError("Foldback paired spans must have equal nucleotide counts.")
        if len(self.pairs) != self.retained_tract_span.length.value:
            raise ValueError("Foldback pairs must cover every retained-tract nucleotide.")

        left_indexes: set[int] = set()
        right_indexes: set[int] = set()
        for position, pair in enumerate(self.pairs):
            if not self.retained_tract_span.contains_index(pair.left_index):
                raise ValueError("Foldback pair left index lies outside retained tract.")
            if not self.foldback_arm_span.contains_index(pair.right_index):
                raise ValueError("Foldback pair right index lies outside foldback arm.")
            if pair.left_index in left_indexes or pair.right_index in right_indexes:
                raise ValueError("Foldback pair nucleotide indexes must be unique.")
            expected_left = self.retained_tract_span.start.offset + position
            expected_right = self.foldback_arm_span.end.offset - 1 - position
            if pair.left_index != expected_left or pair.right_index != expected_right:
                raise ValueError("Foldback pairs must use antiparallel position order.")
            if (
                pair.left_base != self.sequence[pair.left_index]
                or pair.right_base != self.sequence[pair.right_index]
            ):
                raise ValueError("Foldback pair bases must match the junction sequence.")
            left_indexes.add(pair.left_index)
            right_indexes.add(pair.right_index)
        return self


class BasalJunction(HopModel):
    """The paired junction at the open end of the payload duplex."""

    junction_id: ReferenceId
    left_arm: str
    right_arm: str
    pair_count: BasePairCount
    pairs: tuple[JunctionPairObservation, ...] = Field(min_length=1)

    @field_validator("left_arm", "right_arm", mode="before")
    @classmethod
    def normalize_arm(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_pairing(self) -> BasalJunction:
        if not self.left_arm or len(self.left_arm) != len(self.right_arm):
            raise ValueError("Basal-junction arms must have equal nonzero lengths.")
        if self.pair_count.value != len(self.left_arm):
            raise ValueError("Basal-junction pair count must equal each arm length.")
        if len(self.pairs) != self.pair_count.value:
            raise ValueError("Basal-junction pairs must equal the declared pair count.")
        for position, pair in enumerate(self.pairs):
            expected_right = len(self.right_arm) - 1 - position
            if pair.left_index != position or pair.right_index != expected_right:
                raise ValueError("Basal-junction pairs must use antiparallel arm order.")
            if (
                pair.left_base != self.left_arm[pair.left_index]
                or pair.right_base != self.right_arm[pair.right_index]
            ):
                raise ValueError("Basal-junction pair bases must match the declared arms.")
        return self


__all__ = [
    "BasalJunction",
    "FoldbackJunction",
    "JunctionPairKind",
    "JunctionPairObservation",
    "Strand",
]
