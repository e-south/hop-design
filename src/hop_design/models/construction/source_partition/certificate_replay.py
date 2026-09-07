"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source_partition/certificate_replay.py

Builds full-span fragment certificates from exact source-partition replay states.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.catalog import ResolvedNickSite
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import Fragment, StrandEnd

from .certificate import (
    SourcePartitionBoundaryKind,
    SourcePartitionCertificate,
    SourcePartitionFragmentBoundary,
    SourcePartitionFragmentCertificate,
    SourcePartitionFragmentDisposition,
)
from .policy import SourcePartitionThresholdAssessment
from .request import SourcePartitionDiscoveryRequest


def _fragment_boundary(
    *,
    strand: Strand,
    offset: int,
    source_length: int,
    sites: tuple[ResolvedNickSite, ...],
) -> SourcePartitionFragmentBoundary:
    enzyme_ids = tuple(
        sorted(
            site.agent_id
            for site in sites
            if site.nick.strand is strand and site.nick.boundary.offset == offset
        )
    )
    if enzyme_ids:
        return SourcePartitionFragmentBoundary(
            source_offset=offset,
            kind=SourcePartitionBoundaryKind.CLEAVAGE,
            enzyme_ids=enzyme_ids,
        )
    physical_end = {
        (Strand.TOP, 0): StrandEnd.FIVE_PRIME,
        (Strand.TOP, source_length): StrandEnd.THREE_PRIME,
        (Strand.BOTTOM, 0): StrandEnd.THREE_PRIME,
        (Strand.BOTTOM, source_length): StrandEnd.FIVE_PRIME,
    }.get((strand, offset))
    if physical_end is None:
        raise ValueError("Every internal fragment boundary requires exact cleavage evidence.")
    return SourcePartitionFragmentBoundary(
        source_offset=offset,
        kind=SourcePartitionBoundaryKind.PHYSICAL_END,
        physical_end=physical_end,
    )


def _certified_fragment(
    fragment: Fragment,
    *,
    required: dict[tuple[Strand, int, int], str],
    source_length: int,
    sites: tuple[ResolvedNickSite, ...],
) -> SourcePartitionFragmentCertificate:
    key = (
        fragment.precursor_strand,
        fragment.precursor_span.start.offset,
        fragment.precursor_span.end.offset,
    )
    return SourcePartitionFragmentCertificate(
        fragment_id=fragment.fragment_id,
        precursor_strand=fragment.precursor_strand,
        source_span=fragment.precursor_span,
        length_nt=len(fragment.sequence),
        disposition=(
            SourcePartitionFragmentDisposition.REQUIRED
            if key in required
            else SourcePartitionFragmentDisposition.SACRIFICIAL
        ),
        survivor_id=required.get(key),
        left_boundary=_fragment_boundary(
            strand=fragment.precursor_strand,
            offset=fragment.precursor_span.start.offset,
            source_length=source_length,
            sites=sites,
        ),
        right_boundary=_fragment_boundary(
            strand=fragment.precursor_strand,
            offset=fragment.precursor_span.end.offset,
            source_length=source_length,
            sites=sites,
        ),
    )


def _threshold_assessment(
    threshold: int,
    fragments: tuple[SourcePartitionFragmentCertificate, ...],
) -> SourcePartitionThresholdAssessment:
    violations = tuple(
        sorted(
            item.fragment_id
            for item in fragments
            if (
                item.disposition is SourcePartitionFragmentDisposition.SACRIFICIAL
                and item.length_nt > threshold
            )
            or (
                item.disposition is SourcePartitionFragmentDisposition.REQUIRED
                and item.length_nt <= threshold
            )
        )
    )
    return SourcePartitionThresholdAssessment(
        maximum_sacrificial_fragment_nt=threshold,
        feasible=not violations,
        violating_fragment_ids=violations,
    )


def build_source_partition_certificate(
    request: SourcePartitionDiscoveryRequest,
    *,
    fragments: tuple[Fragment, ...],
    sites: tuple[ResolvedNickSite, ...],
) -> SourcePartitionCertificate | None:
    """Certify every fragment and return the least-permissive successful threshold."""
    required = {
        (
            survivor.precursor_strand,
            survivor.source_span.start.offset,
            survivor.source_span.end.offset,
        ): survivor.survivor_id
        for survivor in request.constraints.required_survivors
    }
    source_length = len(request.source.top_sequence_5prime)
    strand_order = {Strand.TOP: 0, Strand.BOTTOM: 1}
    certified = tuple(
        sorted(
            (
                _certified_fragment(
                    fragment,
                    required=required,
                    source_length=source_length,
                    sites=sites,
                )
                for fragment in fragments
            ),
            key=lambda item: (
                strand_order[item.precursor_strand],
                item.source_span.start.offset,
                item.source_span.end.offset,
            ),
        )
    )
    thresholds = tuple(
        _threshold_assessment(threshold, certified)
        for threshold in request.constraints.fragment_policy.thresholds
    )
    selected = next(
        (item.maximum_sacrificial_fragment_nt for item in thresholds if item.feasible),
        None,
    )
    if selected is None:
        return None
    return SourcePartitionCertificate(
        source_length_nt=source_length,
        fragment_policy=request.constraints.fragment_policy,
        selected_maximum_sacrificial_fragment_nt=selected,
        thresholds=thresholds,
        fragments=certified,
    )


__all__ = ["build_source_partition_certificate"]
