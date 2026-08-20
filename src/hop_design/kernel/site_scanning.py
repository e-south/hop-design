"""Pure IUPAC motif classification and concrete processing-site scanning."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Literal

from hop_design.models.catalog import (
    MotifMatch,
    MotifPresence,
    MotifPresenceReport,
    NickingAgent,
    ReleaseAgent,
    ResolvedNickSite,
    ResolvedReleaseSite,
    SiteOrientation,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.sequence import (
    iupac_bases,
    normalize_dna_sequence,
    reverse_complement_iupac,
)
from hop_design.models.strand_state import DuplexCut, NickEvent


def _orientation_motifs(motif: str) -> Iterator[tuple[SiteOrientation, str]]:
    yield SiteOrientation.FORWARD, motif
    reverse = reverse_complement_iupac(motif)
    if reverse != motif:
        yield SiteOrientation.REVERSE, reverse


PresentMotif = Literal[MotifPresence.GUARANTEED, MotifPresence.POSSIBLE]


def _matching_windows(
    sequence: str, motif: str
) -> Iterator[tuple[int, SiteOrientation, str, PresentMotif]]:
    for orientation, oriented_motif in _orientation_motifs(motif):
        for start in range(len(sequence) - len(oriented_motif) + 1):
            window = sequence[start : start + len(oriented_motif)]
            overlaps = tuple(
                iupac_bases(sequence_symbol) & iupac_bases(motif_symbol)
                for sequence_symbol, motif_symbol in zip(window, oriented_motif, strict=True)
            )
            if any(not bases for bases in overlaps):
                continue
            guaranteed = all(
                iupac_bases(sequence_symbol) <= iupac_bases(motif_symbol)
                for sequence_symbol, motif_symbol in zip(window, oriented_motif, strict=True)
            )
            certainty: PresentMotif = (
                MotifPresence.GUARANTEED if guaranteed else MotifPresence.POSSIBLE
            )
            yield start, orientation, window, certainty


def classify_motif_presence(*, sequence: str, motif: str) -> MotifPresenceReport:
    """Classify a motif as guaranteed, possible, or absent in symbolic DNA."""
    normalized_sequence = normalize_dna_sequence(sequence, allow_degenerate=True)
    normalized_motif = normalize_dna_sequence(motif, allow_degenerate=True)
    matches = tuple(
        MotifMatch(
            span=Span(
                start=Boundary(offset=start),
                end=Boundary(offset=start + len(normalized_motif)),
            ),
            orientation=orientation,
            matched_symbols=window,
            certainty=certainty,
        )
        for start, orientation, window, certainty in _matching_windows(
            normalized_sequence, normalized_motif
        )
    )
    if any(match.certainty is MotifPresence.GUARANTEED for match in matches):
        status = MotifPresence.GUARANTEED
    elif matches:
        status = MotifPresence.POSSIBLE
    else:
        status = MotifPresence.ABSENT
    return MotifPresenceReport(status=status, matches=matches)


def scan_nicking_agent(sequence: str, *, agent: NickingAgent) -> tuple[ResolvedNickSite, ...]:
    """Resolve concrete nick events for both motif orientations."""
    normalized = normalize_dna_sequence(sequence, allow_degenerate=False)
    motif_nt = len(agent.motif_top_5to3)
    matches: list[ResolvedNickSite] = []
    for start, orientation, window, _certainty in _matching_windows(
        normalized, agent.motif_top_5to3
    ):
        if orientation is SiteOrientation.FORWARD:
            strand = agent.nicked_strand
            boundary = start + agent.cut_offset
        else:
            strand = Strand.BOTTOM if agent.nicked_strand is Strand.TOP else Strand.TOP
            boundary = start + motif_nt - agent.cut_offset
        if boundary < 0 or boundary > len(normalized):
            continue
        matches.append(
            ResolvedNickSite(
                agent_id=agent.agent_id,
                site_span=Span(
                    start=Boundary(offset=start),
                    end=Boundary(offset=start + motif_nt),
                ),
                orientation=orientation,
                matched_sequence=window,
                nick=NickEvent(boundary=Boundary(offset=boundary), strand=strand),
            )
        )
    return tuple(
        sorted(matches, key=lambda match: (match.site_span.start.offset, match.orientation))
    )


def scan_release_agent(sequence: str, *, agent: ReleaseAgent) -> tuple[ResolvedReleaseSite, ...]:
    """Resolve concrete duplex cuts for both motif orientations."""
    normalized = normalize_dna_sequence(sequence, allow_degenerate=False)
    motif_nt = len(agent.motif_top_5to3)
    matches: list[ResolvedReleaseSite] = []
    for start, orientation, window, _certainty in _matching_windows(
        normalized, agent.motif_top_5to3
    ):
        if orientation is SiteOrientation.FORWARD:
            top_cut = start + agent.top_cut_offset
            bottom_cut = start + agent.bottom_cut_offset
        else:
            top_cut = start + motif_nt - agent.bottom_cut_offset
            bottom_cut = start + motif_nt - agent.top_cut_offset
        if not (0 <= top_cut <= len(normalized) and 0 <= bottom_cut <= len(normalized)):
            continue
        matches.append(
            ResolvedReleaseSite(
                agent_id=agent.agent_id,
                site_span=Span(
                    start=Boundary(offset=start),
                    end=Boundary(offset=start + motif_nt),
                ),
                orientation=orientation,
                matched_sequence=window,
                cut=DuplexCut(
                    top=Boundary(offset=top_cut),
                    bottom=Boundary(offset=bottom_cut),
                ),
            )
        )
    return tuple(
        sorted(matches, key=lambda match: (match.site_span.start.offset, match.orientation))
    )


__all__ = [
    "classify_motif_presence",
    "scan_nicking_agent",
    "scan_release_agent",
]
