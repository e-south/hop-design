"""Strict contracts for basal-junction pairing and caller-owned policy."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.diagnostics import CheckReport, Severity
from hop_design.models.junction import (
    BasalJunction,
    JunctionPairKind,
    JunctionPairObservation,
)
from hop_design.models.sequence import (
    SequenceValidationError,
    normalize_dna_sequence,
)
from hop_design.models.strand_state import NickEvent

BasalPairKind = JunctionPairKind


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
            (self.kind is BasalPairKind.WATSON_CRICK and self.compact_symbol == "M")
            or (self.kind is BasalPairKind.GT_WOBBLE and self.compact_symbol == "W")
            or (self.kind is BasalPairKind.HARD_MISMATCH and self.compact_symbol == "X")
        )
        if not consistent:
            raise ValueError("Basal pair kind and compact symbol must match the physical bases.")
        return self


class BasalPairingRequest(HopModel):
    """Two explicit four-nucleotide arms and a wobble interpretation choice."""

    left_arm: str
    right_arm: str
    allow_gt_wobble: bool

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
    """Derived physical profile; compact M/W/X labels are interoperability fields."""

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
    support_score: float = Field(ge=0.0, le=4.0)
    disruption_score: float = Field(ge=0.0, le=4.0)
    terminal_pair_kind: BasalPairKind

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
            pair.kind is BasalPairKind.HARD_MISMATCH for pair in self.pairs[1:3]
        )
        if self.middle_hard_mismatch_count != expected_middle_hard:
            raise ValueError("middle_hard_mismatch_count must match S2 and S1 observations.")
        if self.support_score != self.watson_crick_count + 0.5 * self.wobble_count:
            raise ValueError("support_score must use M=1, W=0.5, X=0 weights.")
        if self.disruption_score != self.hard_mismatch_count + 0.5 * self.wobble_count:
            raise ValueError("disruption_score must use X=1, W=0.5, M=0 weights.")
        if self.terminal_pair_kind is not self.pairs[-1].kind:
            raise ValueError("terminal_pair_kind must equal the S0 pair kind.")
        return self


def _normalize_profiles(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(value.strip().upper() for value in values)
    if any(len(value) != 4 or set(value) - set("MWX") for value in normalized):
        raise ValueError("Compact profiles must contain exactly four M/W/X symbols.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Compact profile lists must not contain duplicates.")
    return normalized


class BasalConstraintProfile(HopModel):
    """Explicit caller policy for classifying a physical basal pair profile."""

    require_terminal_watson_crick: bool
    max_active_hard_mismatches: int = Field(ge=0, le=4)
    max_active_non_watson_crick_pairs: int = Field(ge=0, le=4)
    forbid_active_middle_double_hard: bool
    minimum_active_support: float = Field(ge=0.0, le=4.0)
    maximum_active_disruption: float = Field(ge=0.0, le=4.0)
    require_outer_hard_for_active_double: bool
    reject_compact_profiles: tuple[str, ...]
    reserve_compact_profiles: tuple[str, ...]

    @field_validator("reject_compact_profiles", "reserve_compact_profiles", mode="after")
    @classmethod
    def normalize_profiles(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_profiles(values)

    @model_validator(mode="after")
    def validate_disjoint_buckets(self) -> BasalConstraintProfile:
        overlap = sorted(set(self.reject_compact_profiles) & set(self.reserve_compact_profiles))
        if overlap:
            raise ValueError("A compact profile cannot be both rejected and reserved.")
        return self


class BasalDesignRequest(HopModel):
    """Physical arms, explicit policy, and optional terminal processing."""

    pairing: BasalPairingRequest
    constraints: BasalConstraintProfile
    acceptance: Literal["active_only", "allow_reserve"]
    terminal_nick: NickEvent | None = None

    @model_validator(mode="after")
    def validate_terminal_boundary(self) -> BasalDesignRequest:
        if self.terminal_nick is not None and self.terminal_nick.boundary.offset != len(
            self.pairing.left_arm
        ):
            raise ValueError("Basal terminal nick boundary must equal the paired-arm length.")
        return self


class BasalPolicyStatus(StrEnum):
    ACTIVE = "active"
    RESERVE = "reserve"
    REJECT = "reject"


class BasalPolicyReason(StrEnum):
    ACTIVE = "active_profile"
    TERMINAL_PAIR = "terminal_pair_not_watson_crick"
    EXPLICIT_REJECT = "explicitly_rejected_profile"
    EXPLICIT_RESERVE = "explicitly_reserved_profile"
    NON_WATSON_CRICK_LIMIT = "too_many_non_watson_crick_pairs"
    HARD_MISMATCH_LIMIT = "too_many_hard_mismatches"
    MIDDLE_DOUBLE_HARD = "middle_double_hard_mismatch"
    SUPPORT = "insufficient_support"
    DISRUPTION = "excessive_disruption"
    DOUBLE_WITHOUT_OUTER_HARD = "double_hard_without_outer_hard_mismatch"


class BasalPolicyDecision(HopModel):
    status: BasalPolicyStatus
    reason: BasalPolicyReason

    @model_validator(mode="after")
    def validate_status_reason(self) -> BasalPolicyDecision:
        allowed_reasons = {
            BasalPolicyStatus.ACTIVE: {BasalPolicyReason.ACTIVE},
            BasalPolicyStatus.REJECT: {
                BasalPolicyReason.TERMINAL_PAIR,
                BasalPolicyReason.EXPLICIT_REJECT,
            },
            BasalPolicyStatus.RESERVE: {
                BasalPolicyReason.EXPLICIT_RESERVE,
                BasalPolicyReason.NON_WATSON_CRICK_LIMIT,
                BasalPolicyReason.HARD_MISMATCH_LIMIT,
                BasalPolicyReason.MIDDLE_DOUBLE_HARD,
                BasalPolicyReason.SUPPORT,
                BasalPolicyReason.DISRUPTION,
                BasalPolicyReason.DOUBLE_WITHOUT_OUTER_HARD,
            },
        }
        if self.reason not in allowed_reasons[self.status]:
            raise ValueError("Basal policy status and reason must describe one decision.")
        return self


class BasalEvaluation(HopModel):
    junction: BasalJunction
    profile: BasalPairProfile
    decision: BasalPolicyDecision
    report: CheckReport

    @model_validator(mode="after")
    def validate_junction_projection(self) -> BasalEvaluation:
        junction_pairs = tuple(
            (
                pair.left_index,
                pair.right_index,
                pair.left_base,
                pair.right_base,
                pair.kind,
            )
            for pair in self.junction.pairs
        )
        profile_pairs = tuple(
            (
                pair.left_index,
                pair.right_index,
                pair.left_base,
                pair.right_base,
                pair.kind,
            )
            for pair in self.profile.pairs
        )
        if (
            self.junction.left_arm != self.profile.left_arm
            or self.junction.right_arm != self.profile.right_arm
            or junction_pairs != profile_pairs
        ):
            raise ValueError("Basal evaluation junction must equal its physical pair profile.")
        expected_diagnostics = {
            BasalPolicyStatus.ACTIVE: (),
            BasalPolicyStatus.RESERVE: (("HOP-BASAL-002", Severity.WARNING),),
            BasalPolicyStatus.REJECT: (("HOP-BASAL-001", Severity.ERROR),),
        }
        actual_diagnostics = tuple(
            (diagnostic.code, diagnostic.severity) for diagnostic in self.report.diagnostics
        )
        if actual_diagnostics != expected_diagnostics[self.decision.status]:
            raise ValueError("Basal policy decision and report must agree.")
        return self


__all__ = [
    "BasalConstraintProfile",
    "BasalDesignRequest",
    "BasalEvaluation",
    "BasalPairKind",
    "BasalPairObservation",
    "BasalPairProfile",
    "BasalPairingRequest",
    "BasalPolicyDecision",
    "BasalPolicyReason",
    "BasalPolicyStatus",
]
