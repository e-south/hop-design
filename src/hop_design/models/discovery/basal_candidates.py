"""Strict contracts for bounded basal-junction candidate discovery."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.basal import (
    BasalConstraintProfile,
    BasalEvaluation,
    BasalPairingRequest,
    BasalPairKind,
    BasalPolicyDecision,
    BasalPolicyReason,
    BasalPolicyStatus,
)
from hop_design.models.base import HopModel
from hop_design.models.sequence import (
    SequenceValidationError,
    iupac_bases,
    normalize_dna_sequence,
)

BasalCandidateAcceptance = Literal["active_only", "allow_reserve"]
BasalCandidateSearchStatus = Literal["complete", "infeasible", "truncated"]
BasalCandidateSearchTruncation = Literal["max_search_nodes", "max_hits"]


class BasalCandidateExclusionStatus(StrEnum):
    """Policy outcomes that make a pairing unavailable to one search request."""

    RESERVE = "reserve"
    REJECT = "reject"


class BasalCandidateSearchRequest(HopModel):
    """Caller-authored arm domains and explicit selection policy."""

    schema_id: Literal["hop.basal-candidate-search/v1"] = Field(
        default="hop.basal-candidate-search/v1",
        alias="schema",
    )
    left_arm_template: str
    right_arm_template: str
    allow_gt_wobble: bool
    constraints: BasalConstraintProfile
    acceptance: BasalCandidateAcceptance

    @field_validator("left_arm_template", "right_arm_template", mode="before")
    @classmethod
    def normalize_arm_template(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        normalized = normalize_dna_sequence(value, allow_degenerate=True)
        if len(normalized) != 4:
            raise ValueError("Basal candidate arm templates must contain four nucleotides.")
        return normalized


class BasalCandidateSearchLimits(HopModel):
    """Hard budgets for arm-pair evaluation and returned candidates."""

    max_search_nodes: int = Field(ge=1)
    max_hits: int = Field(ge=1)


class BasalCandidateExclusionSummary(HopModel):
    """Aggregate policy decision for evaluated, non-returnable candidates."""

    status: BasalCandidateExclusionStatus
    reason: BasalPolicyReason
    count: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_decision(self) -> BasalCandidateExclusionSummary:
        BasalPolicyDecision(
            status=BasalPolicyStatus(self.status.value),
            reason=self.reason,
        )
        return self


def basal_candidate_id(
    *,
    pairing: BasalPairingRequest,
    evaluation: BasalEvaluation,
) -> str:
    """Return the full content identity for one evaluated basal candidate."""
    payload = {
        "evaluation": evaluation.model_dump(mode="json", by_alias=True),
        "pairing": pairing.model_dump(mode="json", by_alias=True),
    }
    content = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")
    return f"hop:basal-candidate/{hashlib.sha256(content).hexdigest()}@1"


class BasalCandidate(HopModel):
    """One exact evaluated arm pair in canonical physical order."""

    candidate_id: str = Field(pattern=r"^hop:basal-candidate/[0-9a-f]{64}@1$")
    rank: int = Field(ge=1)
    pairing: BasalPairingRequest
    evaluation: BasalEvaluation

    @model_validator(mode="after")
    def validate_projection(self) -> BasalCandidate:
        if (
            self.pairing.left_arm != self.evaluation.profile.left_arm
            or self.pairing.right_arm != self.evaluation.profile.right_arm
        ):
            raise ValueError("Candidate pairing must equal its basal evaluation arms.")
        for pair in self.evaluation.profile.pairs:
            literal_gt = (pair.left_base, pair.right_base) in {("G", "T"), ("T", "G")}
            expected = (
                BasalPairKind.GT_WOBBLE
                if literal_gt and self.pairing.allow_gt_wobble
                else BasalPairKind.HARD_MISMATCH
            )
            if pair.kind is BasalPairKind.WATSON_CRICK:
                continue
            if pair.kind is not expected:
                raise ValueError("Candidate pair calls must honor allow_gt_wobble.")
        expected_id = basal_candidate_id(pairing=self.pairing, evaluation=self.evaluation)
        if self.candidate_id != expected_id:
            raise ValueError("Basal candidate_id must match the evaluated candidate content.")
        return self


def basal_candidate_order_key(candidate: BasalCandidate) -> tuple[str, str, str, str]:
    """Return a canonical order without encoding application desirability."""
    return (
        candidate.evaluation.profile.compact_profile_s3_s2_s1_s0,
        candidate.pairing.left_arm,
        candidate.pairing.right_arm,
        candidate.candidate_id,
    )


class BasalCandidateSearchResult(HopModel):
    """Bounded arm-pair search with explicit exclusions and truncation."""

    status: BasalCandidateSearchStatus
    request: BasalCandidateSearchRequest
    limits: BasalCandidateSearchLimits
    hits: tuple[BasalCandidate, ...]
    candidate_space_size: int = Field(ge=1)
    search_nodes_examined: int = Field(ge=0)
    observed_hit_count: int = Field(ge=0)
    excluded: tuple[BasalCandidateExclusionSummary, ...]
    truncated_by: tuple[BasalCandidateSearchTruncation, ...] = ()

    @model_validator(mode="after")
    def validate_accounting(self) -> BasalCandidateSearchResult:
        expected_space = 1
        for symbol in self.request.left_arm_template + self.request.right_arm_template:
            expected_space *= len(iupac_bases(symbol))
        if self.candidate_space_size != expected_space:
            raise ValueError("candidate_space_size must equal the declared IUPAC domains.")
        expected_examined = min(
            self.candidate_space_size,
            self.limits.max_search_nodes,
        )
        if self.search_nodes_examined != expected_examined:
            raise ValueError("search_nodes_examined must exhaust the available node budget.")
        if self.observed_hit_count > self.search_nodes_examined:
            raise ValueError("observed_hit_count cannot exceed examined search nodes.")
        expected_returned = min(self.observed_hit_count, self.limits.max_hits)
        if len(self.hits) != expected_returned:
            raise ValueError("Returned hits must exhaust the available hit budget.")
        if sum(summary.count for summary in self.excluded) != (
            self.search_nodes_examined - self.observed_hit_count
        ):
            raise ValueError("Excluded candidate counts must cover every examined non-hit.")
        exclusion_keys = tuple((summary.status, summary.reason) for summary in self.excluded)
        if len(set(exclusion_keys)) != len(exclusion_keys):
            raise ValueError("Excluded candidate summaries must be unique.")
        if exclusion_keys != tuple(sorted(exclusion_keys, key=lambda item: (item[0], item[1]))):
            raise ValueError("Excluded candidate summaries must use canonical order.")

        expected_truncation: list[BasalCandidateSearchTruncation] = []
        if self.search_nodes_examined < self.candidate_space_size:
            expected_truncation.append("max_search_nodes")
        if self.observed_hit_count > self.limits.max_hits:
            expected_truncation.append("max_hits")
        if self.truncated_by != tuple(expected_truncation):
            raise ValueError("truncated_by must exactly describe node and hit truncation.")
        if (self.status == "truncated") != bool(self.truncated_by):
            raise ValueError("Truncated status and truncation evidence must agree.")
        if self.status == "infeasible":
            if self.search_nodes_examined != self.candidate_space_size:
                raise ValueError("An infeasible search must examine the complete candidate space.")
            if self.observed_hit_count or self.hits:
                raise ValueError("An infeasible search cannot contain candidates.")
        if self.status == "complete":
            if self.search_nodes_examined != self.candidate_space_size:
                raise ValueError("A complete search must examine the complete candidate space.")
            if not self.hits or len(self.hits) != self.observed_hit_count:
                raise ValueError("A complete search must return every observed candidate.")

        expected_ranks = tuple(range(1, len(self.hits) + 1))
        if tuple(candidate.rank for candidate in self.hits) != expected_ranks:
            raise ValueError("Returned basal candidate ranks must be contiguous and one-based.")
        if tuple(self.hits) != tuple(sorted(self.hits, key=basal_candidate_order_key)):
            raise ValueError("Returned candidates must use canonical physical order.")

        allowed_statuses = {BasalPolicyStatus.ACTIVE}
        if self.request.acceptance == "allow_reserve":
            allowed_statuses.add(BasalPolicyStatus.RESERVE)
        for candidate in self.hits:
            if candidate.evaluation.decision.status not in allowed_statuses:
                raise ValueError("Returned candidate violates the request acceptance policy.")
            for base, symbol in zip(
                candidate.pairing.left_arm,
                self.request.left_arm_template,
                strict=True,
            ):
                if base not in iupac_bases(symbol):
                    raise ValueError("Returned left arm lies outside its caller-authored domain.")
            for base, symbol in zip(
                candidate.pairing.right_arm,
                self.request.right_arm_template,
                strict=True,
            ):
                if base not in iupac_bases(symbol):
                    raise ValueError("Returned right arm lies outside its caller-authored domain.")
            if candidate.pairing.allow_gt_wobble is not self.request.allow_gt_wobble:
                raise ValueError("Returned candidate wobble interpretation must match the request.")
        return self


__all__ = [
    "BasalCandidate",
    "BasalCandidateExclusionStatus",
    "BasalCandidateExclusionSummary",
    "BasalCandidateSearchLimits",
    "BasalCandidateSearchRequest",
    "BasalCandidateSearchResult",
]
