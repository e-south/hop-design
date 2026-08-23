"""Strict contracts for optional paired stem context outside the payload."""

from __future__ import annotations

from pydantic import field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import BasePairCount
from hop_design.models.junction import JunctionPairKind, JunctionPairObservation
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence


class PairedStemExtensionRequest(HopModel):
    """Two literal arms for paired stem context between basal junction and payload."""

    left_arm: str
    right_arm: str

    @field_validator("left_arm", "right_arm", mode="before")
    @classmethod
    def normalize_arm(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        if not value or value.isspace():
            return ""
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_lengths(self) -> PairedStemExtensionRequest:
        if not self.left_arm or len(self.left_arm) != len(self.right_arm):
            raise ValueError("Paired-stem-extension arms must have equal nonzero lengths.")
        return self


class PairedStemExtension(HopModel):
    """Derived physical pairing for optional non-payload stem context."""

    left_arm: str
    right_arm: str
    pair_count: BasePairCount
    pairs: tuple[JunctionPairObservation, ...]
    watson_crick_count: int
    wobble_count: int
    hard_mismatch_count: int

    @field_validator("left_arm", "right_arm", mode="before")
    @classmethod
    def normalize_arm(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_derivations(self) -> PairedStemExtension:
        if not self.left_arm or len(self.left_arm) != len(self.right_arm):
            raise ValueError("Paired-stem-extension arms must have equal nonzero lengths.")
        if self.pair_count.value != len(self.left_arm) or len(self.pairs) != len(self.left_arm):
            raise ValueError("Paired-stem-extension pair count must cover both arms.")
        for position, pair in enumerate(self.pairs):
            right_index = len(self.right_arm) - 1 - position
            if pair.left_index != position or pair.right_index != right_index:
                raise ValueError("Paired-stem-extension pairs must use antiparallel order.")
            if (
                pair.left_base != self.left_arm[position]
                or pair.right_base != self.right_arm[right_index]
            ):
                raise ValueError("Paired-stem-extension pair bases must match the literal arms.")
        observed_counts = {
            JunctionPairKind.WATSON_CRICK: self.watson_crick_count,
            JunctionPairKind.GT_WOBBLE: self.wobble_count,
            JunctionPairKind.HARD_MISMATCH: self.hard_mismatch_count,
        }
        if any(
            sum(pair.kind is kind for pair in self.pairs) != count
            for kind, count in observed_counts.items()
        ):
            raise ValueError("Paired-stem-extension counts must match its pair observations.")
        return self


__all__ = ["PairedStemExtension", "PairedStemExtensionRequest"]
