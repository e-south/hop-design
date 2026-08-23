"""Bounded basal-junction candidate enumeration."""

from __future__ import annotations

from collections import Counter
from typing import Literal

from hop_design.design.basal import evaluate_basal_pairing
from hop_design.kernel.basal_candidates import (
    basal_candidate_domains,
    basal_candidate_space_size,
    enumerate_basal_candidate_pairs,
)
from hop_design.models.basal import BasalPairingRequest
from hop_design.models.basal_policy import (
    BasalPolicyReason,
    BasalPolicyStatus,
)
from hop_design.models.discovery.basal_candidates import (
    BasalCandidate,
    BasalCandidateExclusionStatus,
    BasalCandidateExclusionSummary,
    BasalCandidateSearchLimits,
    BasalCandidateSearchRequest,
    BasalCandidateSearchResult,
    BasalCandidateSearchTruncation,
    basal_candidate_id,
    basal_candidate_order_key,
)


def search_basal_candidates(
    request: BasalCandidateSearchRequest,
    *,
    limits: BasalCandidateSearchLimits,
) -> BasalCandidateSearchResult:
    """Enumerate exact basal arm pairs inside caller-authored IUPAC domains."""
    domains = basal_candidate_domains(request)
    candidate_space_size = basal_candidate_space_size(domains)
    accepted = []
    excluded: Counter[tuple[BasalCandidateExclusionStatus, BasalPolicyReason]] = Counter()
    nodes = 0
    for left_arm, right_arm in enumerate_basal_candidate_pairs(domains):
        if nodes >= limits.max_search_nodes:
            break
        pairing = BasalPairingRequest(
            left_arm=left_arm,
            right_arm=right_arm,
        )
        evaluation = evaluate_basal_pairing(pairing, constraints=request.constraints)
        nodes += 1
        decision = evaluation.decision
        selectable = decision.status is BasalPolicyStatus.ACTIVE or (
            request.acceptance == "allow_reserve" and decision.status is BasalPolicyStatus.RESERVE
        )
        if selectable:
            accepted.append((pairing, evaluation))
            continue
        excluded[
            (
                BasalCandidateExclusionStatus(decision.status.value),
                decision.reason,
            )
        ] += 1

    candidates = (
        BasalCandidate(
            candidate_id=basal_candidate_id(pairing=pairing, evaluation=evaluation),
            canonical_ordinal=1,
            pairing=pairing,
            evaluation=evaluation,
        )
        for pairing, evaluation in accepted
    )
    ordered_candidates = sorted(candidates, key=basal_candidate_order_key)
    numbered_candidates = tuple(
        candidate.model_copy(update={"canonical_ordinal": canonical_ordinal})
        for canonical_ordinal, candidate in enumerate(ordered_candidates, start=1)
    )
    returned = numbered_candidates[: limits.max_hits]

    truncated_by: list[BasalCandidateSearchTruncation] = []
    if nodes < candidate_space_size:
        truncated_by.append("max_search_nodes")
    if len(returned) < len(numbered_candidates):
        truncated_by.append("max_hits")
    if truncated_by:
        status: Literal["complete", "infeasible", "truncated"] = "truncated"
    elif returned:
        status = "complete"
    else:
        status = "infeasible"

    return BasalCandidateSearchResult(
        status=status,
        request=request,
        limits=limits,
        hits=returned,
        candidate_space_size=candidate_space_size,
        search_nodes_examined=nodes,
        observed_hit_count=len(numbered_candidates),
        excluded=tuple(
            BasalCandidateExclusionSummary(status=key[0], reason=key[1], count=count)
            for key, count in sorted(
                excluded.items(),
                key=lambda item: (item[0][0], item[0][1]),
            )
        ),
        truncated_by=tuple(truncated_by),
    )


__all__ = ["search_basal_candidates"]
