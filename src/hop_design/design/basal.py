"""Caller-policy evaluation for derived basal-junction pair profiles."""

from __future__ import annotations

from hop_design.kernel.basal import classify_basal_pairing
from hop_design.models.basal import BasalPairingRequest
from hop_design.models.basal_policy import (
    BasalConstraintProfile,
    BasalEvaluation,
    BasalPolicyStatus,
    classify_basal_policy,
)
from hop_design.models.coordinates import BasePairCount
from hop_design.models.diagnostics import CheckReport, Diagnostic, Severity
from hop_design.models.junction import BasalJunction
from hop_design.serialization import canonical_json_bytes, sha256_digest


def evaluate_basal_pairing(
    request: BasalPairingRequest,
    *,
    constraints: BasalConstraintProfile,
) -> BasalEvaluation:
    """Classify physical pairs, then apply one explicit caller constraint profile."""
    profile = classify_basal_pairing(request)
    decision = classify_basal_policy(profile, constraints)
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
        constraints=constraints,
        decision=decision,
        report=CheckReport(diagnostics=diagnostics),
    )


__all__ = ["evaluate_basal_pairing"]
