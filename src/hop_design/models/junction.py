"""Resolved foldback- and basal-junction contracts."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import BasePairCount, Span
from hop_design.models.physical import (
    JunctionPairKind,
    Strand,
    classify_literal_pair,
)
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import (
    SequenceValidationError,
    normalize_dna_sequence,
    reverse_complement_iupac,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest


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
        observed_kind = classify_literal_pair(
            left_base=self.left_base,
            right_base=self.right_base,
        )
        if self.kind is not observed_kind:
            labels = {
                JunctionPairKind.WATSON_CRICK: "Watson-Crick",
                JunctionPairKind.GT_WOBBLE: "G:T wobble",
                JunctionPairKind.HARD_MISMATCH: "Hard-mismatch",
            }
            raise ValueError(
                f"{labels[self.kind]} pair calls must match the literal bases; "
                f"these bases classify as {labels[observed_kind]}."
            )
        return self

    @property
    def aligned_right_base(self) -> str:
        """Return the right base complemented into left-arm display orientation."""
        return reverse_complement_iupac(self.right_base)

    @property
    def is_match(self) -> bool:
        """Return whether this observation is Watson-Crick paired."""
        return self.kind is JunctionPairKind.WATSON_CRICK


def derive_exact_foldback_junction_id(
    *,
    sequence: str,
    retained_nt: int,
    turn_nt: int,
    pairs: tuple[JunctionPairObservation, ...],
) -> str:
    """Return content identity for one exact foldback junction."""
    seed = {
        "sequence": sequence,
        "retained_nt": retained_nt,
        "turn_nt": turn_nt,
        "pairs": [pair.model_dump(mode="json") for pair in pairs],
    }
    digest = sha256_digest(canonical_json_bytes(seed)).removeprefix("sha256:")
    return f"hop:foldback-junction/exact-{digest}@1"


def derive_exact_basal_junction_id(
    *,
    left_arm: str,
    right_arm: str,
    pairs: tuple[JunctionPairObservation, ...],
) -> str:
    """Return content identity for one exact basal junction."""
    seed = {
        "left_arm": left_arm,
        "right_arm": right_arm,
        "pairs": [pair.model_dump(mode="json") for pair in pairs],
    }
    digest = sha256_digest(canonical_json_bytes(seed)).removeprefix("sha256:")
    return f"hop:basal-junction/exact-{digest}@1"


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
    "classify_literal_pair",
    "derive_exact_basal_junction_id",
    "derive_exact_foldback_junction_id",
]
