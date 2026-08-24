"""Bounded concrete precursor discovery for one selected nicking placement."""

from __future__ import annotations

from collections import Counter
from itertools import pairwise
from typing import Literal

from hop_design.design.foldback import evaluate_foldback
from hop_design.kernel.candidates import (
    candidate_base_domains,
    candidate_sequence_count,
    enumerate_candidate_sequences,
)
from hop_design.kernel.site_scanning import scan_nicking_agent
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.discovery import (
    AdditionalNickConstraint,
    CandidateRejectionCode,
    CandidateRejectionSummary,
    CandidateSearchTruncation,
    FoldbackPrecursorCandidate,
    FoldbackPrecursorSearchLimits,
    FoldbackPrecursorSearchRequest,
    FoldbackPrecursorSearchResult,
)
from hop_design.models.discovery.candidates import (
    foldback_precursor_candidate_id,
    foldback_precursor_candidate_order_key,
)
from hop_design.models.foldback import FoldbackConstraints, FoldbackEvaluationRequest
from hop_design.models.sequence import reverse_complement_iupac


def _max_homopolymer_run(sequence: str) -> int:
    longest = 1
    current = 1
    for previous, base in pairwise(sequence):
        current = current + 1 if base == previous else 1
        longest = max(longest, current)
    return longest


def _build_candidate(
    request: FoldbackPrecursorSearchRequest,
    *,
    precursor_sequence: str,
    turn_extension: str,
) -> FoldbackPrecursorCandidate:
    placement = request.placement
    paired_end = placement.nick.boundary.offset + request.target.paired_tract.value
    retained_span = Span(start=placement.nick.boundary, end=Boundary(offset=paired_end))
    retained = precursor_sequence[placement.nick.boundary.offset : paired_end]
    foldback_arm = reverse_complement_iupac(retained)
    evaluation = evaluate_foldback(
        FoldbackEvaluationRequest(
            precursor_sequence=precursor_sequence,
            retained_tract_span=retained_span,
            source_turn_span=Span(
                start=retained_span.end,
                end=Boundary(offset=len(precursor_sequence)),
            ),
            protected_region=placement.site_span,
            turn_extension=turn_extension,
            foldback_arm=foldback_arm,
            constraints=FoldbackConstraints(
                max_non_watson_crick_pairs=0,
                terminal_watson_crick_bp_min=request.target.paired_tract.value,
                terminal_watson_crick_bp_max=request.target.paired_tract.value,
                max_uninterrupted_watson_crick_bp=request.target.paired_tract.value,
                max_added_nt=len(turn_extension) + len(foldback_arm),
                required_turn_nt=request.target.available_turn.value,
                allow_protected_region_non_watson_crick_pairs=False,
            ),
        )
    )
    if evaluation.report.status != "valid":
        raise RuntimeError("A replayed exact foldback candidate failed its derived constraints.")

    sites = scan_nicking_agent(evaluation.designed_sequence, agent=request.agent)
    intended_matches = tuple(
        site
        for site in sites
        if site.site_span == placement.site_span
        and site.orientation is placement.orientation
        and site.nick == placement.nick
    )
    if len(intended_matches) != 1:
        raise RuntimeError("The selected placement did not resolve to exactly one intended site.")
    intended_site = intended_matches[0]
    extra_sites = tuple(site for site in sites if site != intended_site)
    extra_target_nicks = sum(
        site.nick.strand is request.target.nicked_strand for site in extra_sites
    )
    added = f"{turn_extension}{foldback_arm}"
    candidate_id = foldback_precursor_candidate_id(
        precursor_sequence=precursor_sequence,
        turn_extension=turn_extension,
        intended_site=intended_site,
        extra_nick_sites=extra_sites,
        evaluation=evaluation,
    )
    return FoldbackPrecursorCandidate(
        candidate_id=candidate_id,
        precursor_sequence=precursor_sequence,
        turn_extension=turn_extension,
        intended_site=intended_site,
        extra_nick_sites=extra_sites,
        extra_target_strand_nick_count=extra_target_nicks,
        gc_fraction_added=sum(base in "GC" for base in added) / len(added),
        max_homopolymer_run_added=_max_homopolymer_run(added),
        evaluation=evaluation,
    )


def _violates_additional_nick_constraint(
    candidate: FoldbackPrecursorCandidate,
    *,
    constraint: AdditionalNickConstraint,
) -> bool:
    if constraint is AdditionalNickConstraint.ALLOW:
        return False
    if constraint is AdditionalNickConstraint.FORBID_TARGET_STRAND:
        return candidate.extra_target_strand_nick_count > 0
    return bool(candidate.extra_nick_sites)


def search_foldback_precursors(
    request: FoldbackPrecursorSearchRequest,
    *,
    limits: FoldbackPrecursorSearchLimits,
) -> FoldbackPrecursorSearchResult:
    """Construct exact foldback precursors only inside caller-authored IUPAC domains."""
    domains = candidate_base_domains(request)
    if domains is None:
        return FoldbackPrecursorSearchResult(
            status="infeasible",
            request=request,
            limits=limits,
            hits=(),
            candidate_space_size=0,
            search_nodes_examined=0,
            observed_hit_count=0,
            rejections=(CandidateRejectionSummary(code="HOP-CAND-001", count=1),),
            truncated_by=(),
        )

    candidate_space_size = candidate_sequence_count(domains)
    observed_hits: list[FoldbackPrecursorCandidate] = []
    rejection_counts: Counter[CandidateRejectionCode] = Counter()
    nodes = 0
    for precursor_sequence, turn_extension in enumerate_candidate_sequences(
        request,
        domains=domains,
    ):
        if nodes >= limits.max_search_nodes:
            break
        candidate = _build_candidate(
            request,
            precursor_sequence=precursor_sequence,
            turn_extension=turn_extension,
        )
        nodes += 1
        if _violates_additional_nick_constraint(
            candidate,
            constraint=request.additional_nicks,
        ):
            rejection_counts["HOP-CAND-002"] += 1
        else:
            observed_hits.append(candidate)

    ordered_hits = sorted(observed_hits, key=foldback_precursor_candidate_order_key)
    returned_hits = tuple(ordered_hits[: limits.max_hits])
    truncated_by: list[CandidateSearchTruncation] = []
    if nodes < candidate_space_size:
        truncated_by.append("max_search_nodes")
    if len(returned_hits) < len(ordered_hits):
        truncated_by.append("max_hits")
    if truncated_by:
        status: Literal["complete", "infeasible", "truncated"] = "truncated"
    elif returned_hits:
        status = "complete"
    else:
        status = "infeasible"
    return FoldbackPrecursorSearchResult(
        status=status,
        request=request,
        limits=limits,
        hits=returned_hits,
        candidate_space_size=candidate_space_size,
        search_nodes_examined=nodes,
        observed_hit_count=len(ordered_hits),
        rejections=tuple(
            CandidateRejectionSummary(code=code, count=count)
            for code, count in sorted(rejection_counts.items())
        ),
        truncated_by=tuple(truncated_by),
    )


__all__ = ["search_foldback_precursors"]
