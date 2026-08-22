"""Pure IUPAC domain intersection and sequence enumeration."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import product
from math import prod

from hop_design.models.discovery import FoldbackPrecursorSearchRequest
from hop_design.models.sequence import iupac_bases


def candidate_base_domains(
    request: FoldbackPrecursorSearchRequest,
) -> tuple[tuple[str, ...], ...] | None:
    """Intersect caller-authored domains with the selected recognition motif."""
    precursor_domains = [
        tuple(sorted(iupac_bases(symbol))) for symbol in request.precursor_template
    ]
    site_start = request.placement.site_span.start.offset
    for offset, motif_symbol in enumerate(request.placement.oriented_motif_5to3):
        index = site_start + offset
        overlap = tuple(sorted(set(precursor_domains[index]) & iupac_bases(motif_symbol)))
        if not overlap:
            return None
        precursor_domains[index] = overlap
    extension_domains = [
        tuple(sorted(iupac_bases(symbol))) for symbol in request.turn_extension_template
    ]
    return (*precursor_domains, *extension_domains)


def candidate_sequence_count(domains: tuple[tuple[str, ...], ...]) -> int:
    """Return exact cardinality before allocating sequence candidates."""
    return prod(len(domain) for domain in domains)


def enumerate_candidate_sequences(
    request: FoldbackPrecursorSearchRequest,
    *,
    domains: tuple[tuple[str, ...], ...],
) -> Iterator[tuple[str, str]]:
    """Yield exact precursor and extension sequences in deterministic lexical order."""
    precursor_nt = len(request.precursor_template)
    for bases in product(*domains):
        sequence = "".join(bases)
        yield sequence[:precursor_nt], sequence[precursor_nt:]


__all__ = [
    "candidate_base_domains",
    "candidate_sequence_count",
    "enumerate_candidate_sequences",
]
