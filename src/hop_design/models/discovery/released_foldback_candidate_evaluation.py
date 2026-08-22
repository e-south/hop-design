"""Pure caller-domain intersection for one released-foldback geometry."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import product
from math import prod

from hop_design.models.discovery.released_foldback_candidates import (
    ReleasedFoldbackPrecursorSearchRequest,
)
from hop_design.models.sequence import iupac_bases


@dataclass(frozen=True)
class ReleasedFoldbackPrecursorDomains:
    """Independent exact-base and correlated-pair choices after intersection."""

    base_domains: tuple[tuple[str, ...], ...]
    pairing_domains: tuple[tuple[str, ...], ...]


def released_foldback_precursor_domains(
    request: ReleasedFoldbackPrecursorSearchRequest,
) -> ReleasedFoldbackPrecursorDomains | None:
    """Intersect one caller template with the selected geometry domains."""
    geometry = request.geometry
    base_domains = [
        tuple(
            base for base in geometry_domain.allowed_bases if base in iupac_bases(template_symbol)
        )
        for geometry_domain, template_symbol in zip(
            geometry.resolved_domains,
            request.precursor_template,
            strict=True,
        )
    ]
    if any(not domain for domain in base_domains):
        return None

    pairing_domains = []
    for pair in geometry.pairing_domains:
        allowed = tuple(
            choice
            for choice in pair.allowed_pairs
            if choice[0] in base_domains[pair.left_coordinate]
            and choice[1] in base_domains[pair.right_coordinate]
        )
        if not allowed:
            return None
        pairing_domains.append(allowed)
    return ReleasedFoldbackPrecursorDomains(
        base_domains=tuple(base_domains),
        pairing_domains=tuple(pairing_domains),
    )


def released_foldback_precursor_candidate_count(
    request: ReleasedFoldbackPrecursorSearchRequest,
    *,
    domains: ReleasedFoldbackPrecursorDomains,
) -> int:
    """Return exact correlated cardinality without allocating candidates."""
    paired_coordinates = {
        coordinate
        for pair in request.geometry.pairing_domains
        for coordinate in (pair.left_coordinate, pair.right_coordinate)
    }
    return prod(
        (
            *(len(domain) for domain in domains.pairing_domains),
            *(
                len(domain)
                for coordinate, domain in enumerate(domains.base_domains)
                if coordinate not in paired_coordinates
            ),
        )
    )


def enumerate_released_foldback_precursors(
    request: ReleasedFoldbackPrecursorSearchRequest,
    *,
    domains: ReleasedFoldbackPrecursorDomains,
) -> Iterator[str]:
    """Yield exact precursors in stable coordinate-first physical order."""
    axes: list[tuple[int, tuple[int, ...], tuple[tuple[str, ...], ...]]] = []
    paired_coordinates: set[int] = set()
    for pair, allowed in zip(
        request.geometry.pairing_domains,
        domains.pairing_domains,
        strict=True,
    ):
        pair_coordinates: tuple[int, ...] = (pair.left_coordinate, pair.right_coordinate)
        paired_coordinates.update(pair_coordinates)
        axes.append(
            (
                pair.left_coordinate,
                pair_coordinates,
                tuple((choice[0], choice[1]) for choice in allowed),
            )
        )
    for coordinate, allowed in enumerate(domains.base_domains):
        if coordinate not in paired_coordinates:
            axes.append((coordinate, (coordinate,), tuple((base,) for base in allowed)))
    axes.sort(key=lambda row: row[0])

    for choices in product(*(axis[2] for axis in axes)):
        sequence = [""] * len(domains.base_domains)
        for (_, axis_coordinates, _), bases in zip(axes, choices, strict=True):
            for coordinate, base in zip(axis_coordinates, bases, strict=True):
                sequence[coordinate] = base
        yield "".join(sequence)


__all__ = [
    "ReleasedFoldbackPrecursorDomains",
    "enumerate_released_foldback_precursors",
    "released_foldback_precursor_candidate_count",
    "released_foldback_precursor_domains",
]
