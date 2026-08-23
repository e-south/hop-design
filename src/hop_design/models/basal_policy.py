"""Caller policy and evaluation contracts for physical basal pair profiles."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.basal import (
    BASAL_PAIRING_INDEX_KIND,
    BasalPairingIndexKind,
    BasalPairingRequest,
    BasalPairProfile,
)
from hop_design.models.base import HopModel
from hop_design.models.diagnostics import CheckReport, Severity
from hop_design.models.junction import BasalJunction, JunctionPairKind
from hop_design.models.strand_state import NickEvent


def _normalize_profiles(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(value.strip().upper() for value in values)
    if any(len(value) != 4 or set(value) - set("MWX") for value in normalized):
        raise ValueError("Compact profiles must contain exactly four M/W/X symbols.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Compact profile lists must not contain duplicates.")
    return normalized


class BasalConstraintProfile(HopModel):
    """Explicit caller policy for classifying a physical basal pair profile."""

    pairing_index_kind: BasalPairingIndexKind = BASAL_PAIRING_INDEX_KIND
    require_terminal_watson_crick: bool
    allow_active_gt_wobble: bool
    max_active_hard_mismatches: int = Field(ge=0, le=4)
    max_active_non_watson_crick_pairs: int = Field(ge=0, le=4)
    forbid_active_middle_double_hard: bool
    minimum_active_pair_support_index: float = Field(ge=0.0, le=4.0)
    maximum_active_pair_disruption_index: float = Field(ge=0.0, le=4.0)
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
    GT_WOBBLE_NOT_ACTIVE = "gt_wobble_not_active"
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
                BasalPolicyReason.GT_WOBBLE_NOT_ACTIVE,
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


def classify_basal_policy(
    profile: BasalPairProfile,
    constraints: BasalConstraintProfile,
) -> BasalPolicyDecision:
    """Apply one explicit policy to an already classified physical pair profile."""
    compact = profile.compact_profile_s3_s2_s1_s0
    if (
        constraints.require_terminal_watson_crick
        and profile.terminal_pair_kind is not JunctionPairKind.WATSON_CRICK
    ):
        return BasalPolicyDecision(
            status=BasalPolicyStatus.REJECT,
            reason=BasalPolicyReason.TERMINAL_PAIR,
        )
    if compact in constraints.reject_compact_profiles:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.REJECT,
            reason=BasalPolicyReason.EXPLICIT_REJECT,
        )
    if compact in constraints.reserve_compact_profiles:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.EXPLICIT_RESERVE,
        )
    if profile.non_watson_crick_count > constraints.max_active_non_watson_crick_pairs:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.NON_WATSON_CRICK_LIMIT,
        )
    if profile.wobble_count and not constraints.allow_active_gt_wobble:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.GT_WOBBLE_NOT_ACTIVE,
        )
    if profile.hard_mismatch_count > constraints.max_active_hard_mismatches:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.HARD_MISMATCH_LIMIT,
        )
    if constraints.forbid_active_middle_double_hard and profile.middle_hard_mismatch_count == 2:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.MIDDLE_DOUBLE_HARD,
        )
    if profile.pair_support_index < constraints.minimum_active_pair_support_index:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.SUPPORT,
        )
    if profile.pair_disruption_index > constraints.maximum_active_pair_disruption_index:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.DISRUPTION,
        )
    if (
        constraints.require_outer_hard_for_active_double
        and profile.hard_mismatch_count == 2
        and profile.pairs[0].kind is not JunctionPairKind.HARD_MISMATCH
    ):
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.DOUBLE_WITHOUT_OUTER_HARD,
        )
    return BasalPolicyDecision(status=BasalPolicyStatus.ACTIVE, reason=BasalPolicyReason.ACTIVE)


class BasalEvaluation(HopModel):
    junction: BasalJunction
    profile: BasalPairProfile
    constraints: BasalConstraintProfile
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
        if self.decision != classify_basal_policy(self.profile, self.constraints):
            raise ValueError("Basal policy decision must derive from the bound constraint profile.")
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
    "BasalPolicyDecision",
    "BasalPolicyReason",
    "BasalPolicyStatus",
    "classify_basal_policy",
]
