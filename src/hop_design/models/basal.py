"""Strict contracts for basal-junction pairing and caller-owned policy."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.junction import (
    JunctionPairKind,
    JunctionPairObservation,
)
from hop_design.models.sequence import (
    SequenceValidationError,
    normalize_dna_sequence,
)

BasalPairingIndexKind = Literal["pair-count-weighted@1"]
BASAL_PAIRING_INDEX_KIND: BasalPairingIndexKind = "pair-count-weighted@1"


class BasalPairObservation(JunctionPairObservation):
    """One physical left:right pair in turn-to-terminal site order."""

    position: int = Field(ge=0, le=3)
    site: Literal["S3", "S2", "S1", "S0"]
    left_index: int = Field(ge=0, le=3)
    right_index: int = Field(ge=0, le=3)
    compact_symbol: Literal["M", "W", "X"]

    @model_validator(mode="after")
    def validate_physical_call(self) -> BasalPairObservation:
        expected_sites = ("S3", "S2", "S1", "S0")
        if self.site != expected_sites[self.position]:
            raise ValueError("Basal pair sites must follow S3, S2, S1, S0 order.")
        if self.left_index != self.position or self.right_index != 3 - self.position:
            raise ValueError("Basal pair indexes must express antiparallel arm alignment.")
        consistent = (
            (self.kind is JunctionPairKind.WATSON_CRICK and self.compact_symbol == "M")
            or (self.kind is JunctionPairKind.GT_WOBBLE and self.compact_symbol == "W")
            or (self.kind is JunctionPairKind.HARD_MISMATCH and self.compact_symbol == "X")
        )
        if not consistent:
            raise ValueError("Basal pair kind and compact symbol must match the physical bases.")
        return self


class BasalPairingRequest(HopModel):
    """Two explicit four-nucleotide arms whose physical pairs are derived."""

    left_arm: str
    right_arm: str

    @field_validator("left_arm", "right_arm", mode="before")
    @classmethod
    def normalize_arm(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        normalized = normalize_dna_sequence(value, allow_degenerate=False)
        if len(normalized) != 4:
            raise ValueError("The S3/S2/S1/S0 basal profile requires four-nucleotide arms.")
        return normalized


class BasalPairProfile(HopModel):
    """Physical pair observations plus explicitly heuristic v1 indices."""

    left_arm: str
    right_arm: str
    site_order: Literal["S3_S2_S1_S0"] = "S3_S2_S1_S0"
    compact_profile_s3_s2_s1_s0: str = Field(pattern=r"^[MWX]{4}$")
    compact_profile_payload_outward: str = Field(pattern=r"^[MWX]{4}$")
    pairs: tuple[
        BasalPairObservation, BasalPairObservation, BasalPairObservation, BasalPairObservation
    ]
    watson_crick_count: int = Field(ge=0, le=4)
    wobble_count: int = Field(ge=0, le=4)
    hard_mismatch_count: int = Field(ge=0, le=4)
    non_watson_crick_count: int = Field(ge=0, le=4)
    middle_hard_mismatch_count: int = Field(ge=0, le=2)
    pairing_index_kind: BasalPairingIndexKind = BASAL_PAIRING_INDEX_KIND
    pair_support_index: float = Field(ge=0.0, le=4.0)
    pair_disruption_index: float = Field(ge=0.0, le=4.0)
    terminal_pair_kind: JunctionPairKind

    @model_validator(mode="after")
    def validate_derivations(self) -> BasalPairProfile:
        symbols = "".join(pair.compact_symbol for pair in self.pairs)
        if self.compact_profile_s3_s2_s1_s0 != symbols:
            raise ValueError("Compact basal profile must match the ordered pair observations.")
        if self.compact_profile_payload_outward != symbols[::-1]:
            raise ValueError("Payload-outward compact profile must reverse S3/S2/S1/S0 order.")
        counts = {
            "M": self.watson_crick_count,
            "W": self.wobble_count,
            "X": self.hard_mismatch_count,
        }
        if any(symbols.count(symbol) != count for symbol, count in counts.items()):
            raise ValueError("Basal pair counts must match the compact profile.")
        if self.non_watson_crick_count != self.wobble_count + self.hard_mismatch_count:
            raise ValueError("non_watson_crick_count must equal wobble plus hard mismatches.")
        expected_middle_hard = sum(
            pair.kind is JunctionPairKind.HARD_MISMATCH for pair in self.pairs[1:3]
        )
        if self.middle_hard_mismatch_count != expected_middle_hard:
            raise ValueError("middle_hard_mismatch_count must match S2 and S1 observations.")
        if self.pair_support_index != self.watson_crick_count + 0.5 * self.wobble_count:
            raise ValueError("pair_support_index must use M=1, W=0.5, X=0 heuristic weights.")
        if self.pair_disruption_index != self.hard_mismatch_count + 0.5 * self.wobble_count:
            raise ValueError("pair_disruption_index must use X=1, W=0.5, M=0 heuristic weights.")
        if self.terminal_pair_kind is not self.pairs[-1].kind:
            raise ValueError("terminal_pair_kind must equal the S0 pair kind.")
        return self


__all__ = [
    "BASAL_PAIRING_INDEX_KIND",
    "BasalPairObservation",
    "BasalPairProfile",
    "BasalPairingIndexKind",
    "BasalPairingRequest",
]
