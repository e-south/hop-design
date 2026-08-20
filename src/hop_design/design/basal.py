"""Caller-policy evaluation for derived basal-junction pair profiles."""

from __future__ import annotations

from hop_design.kernel.basal import classify_basal_pairing
from hop_design.models.basal import (
    BasalConstraintProfile,
    BasalEvaluation,
    BasalPairingRequest,
    BasalPairKind,
    BasalPairProfile,
    BasalPolicyDecision,
    BasalPolicyReason,
    BasalPolicyStatus,
)
from hop_design.models.coordinates import BasePairCount
from hop_design.models.diagnostics import CheckReport, Diagnostic, Severity
from hop_design.models.junction import BasalJunction
from hop_design.serialization import canonical_json_bytes, sha256_digest


def _classify_policy(
    profile: BasalPairProfile, constraints: BasalConstraintProfile
) -> BasalPolicyDecision:
    compact = profile.compact_profile_s3_s2_s1_s0
    if (
        constraints.require_terminal_watson_crick
        and profile.terminal_pair_kind is not BasalPairKind.WATSON_CRICK
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
    if profile.support_score < constraints.minimum_active_support:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.SUPPORT,
        )
    if profile.disruption_score > constraints.maximum_active_disruption:
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.DISRUPTION,
        )
    if (
        constraints.require_outer_hard_for_active_double
        and profile.hard_mismatch_count == 2
        and profile.pairs[0].kind is not BasalPairKind.HARD_MISMATCH
    ):
        return BasalPolicyDecision(
            status=BasalPolicyStatus.RESERVE,
            reason=BasalPolicyReason.DOUBLE_WITHOUT_OUTER_HARD,
        )
    return BasalPolicyDecision(
        status=BasalPolicyStatus.ACTIVE,
        reason=BasalPolicyReason.ACTIVE,
    )


def evaluate_basal_pairing(
    request: BasalPairingRequest,
    *,
    constraints: BasalConstraintProfile,
) -> BasalEvaluation:
    """Classify physical pairs, then apply one explicit caller constraint profile."""
    profile = classify_basal_pairing(request)
    decision = _classify_policy(profile, constraints)
    diagnostics: tuple[Diagnostic, ...]
    if decision.status is BasalPolicyStatus.REJECT:
        diagnostics = (
            Diagnostic(
                code="HOP-BASAL-001",
                severity=Severity.ERROR,
                path="basal_pairing",
                message="The basal pair profile is rejected by the supplied constraint profile.",
                evidence={
                    "compact_profile": profile.compact_profile_s3_s2_s1_s0,
                    "reason": decision.reason.value,
                },
            ),
        )
    elif decision.status is BasalPolicyStatus.RESERVE:
        diagnostics = (
            Diagnostic(
                code="HOP-BASAL-002",
                severity=Severity.WARNING,
                path="basal_pairing",
                message=(
                    "The basal pair profile is reserve-only under the supplied constraint profile."
                ),
                evidence={
                    "compact_profile": profile.compact_profile_s3_s2_s1_s0,
                    "reason": decision.reason.value,
                },
            ),
        )
    else:
        diagnostics = ()
    junction_digest = sha256_digest(canonical_json_bytes(profile)).removeprefix("sha256:")
    return BasalEvaluation(
        junction=BasalJunction(
            junction_id=f"hop:basal-junction/inline-{junction_digest[:16]}@1",
            left_arm=profile.left_arm,
            right_arm=profile.right_arm,
            pair_count=BasePairCount(value=len(profile.pairs)),
            pairs=profile.pairs,
        ),
        profile=profile,
        decision=decision,
        report=CheckReport(diagnostics=diagnostics),
    )


__all__ = ["evaluate_basal_pairing"]
