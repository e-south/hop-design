"""Pure signed-coordinate geometry for terminal basal processing."""

from __future__ import annotations

from math import prod
from typing import Literal

from hop_design.models.catalog import NickingAgent, ReleaseAgent, SiteOrientation
from hop_design.models.discovery.basal_processing import (
    BasalProcessingGeometryBlocker,
    BasalProcessingGeometryFeasibility,
    BasalProcessingGeometryRequest,
    BasalReleaseGeometry,
    RelativeBaseDomain,
)
from hop_design.models.physical import orient_nick_geometry, orient_release_geometry
from hop_design.models.sequence import iupac_bases

_BASES: tuple[Literal["A", "C", "G", "T"], ...] = ("A", "C", "G", "T")
_ALL_BASES = frozenset(_BASES)


def resolve_basal_release_geometry(
    agent: ReleaseAgent,
    *,
    orientation: SiteOrientation,
) -> BasalReleaseGeometry:
    """Normalize one release site so its top cut is signed coordinate zero."""
    geometry = orient_release_geometry(
        motif_top_5to3=agent.motif_top_5to3,
        top_cut_offset=agent.top_cut_offset,
        bottom_cut_offset=agent.bottom_cut_offset,
        orientation=orientation,
    )
    oriented_motif = geometry.motif_top_5to3
    top_offset = geometry.top_cut_offset
    bottom_offset = geometry.bottom_cut_offset
    site_start = -top_offset
    site_end = site_start + len(oriented_motif)
    bottom_cut = site_start + bottom_offset
    return BasalReleaseGeometry(
        release_agent_id=agent.agent_id,
        orientation=orientation,
        oriented_motif_top_5to3=oriented_motif,
        site_start=site_start,
        site_end=site_end,
        bottom_cut=bottom_cut,
        recognition_site_excised=(site_end <= 0 or site_start >= bottom_cut),
    )


def _motif_map(*, motif: str, start: int) -> dict[int, frozenset[str]]:
    return {start + offset: iupac_bases(symbol) for offset, symbol in enumerate(motif)}


def _template_map(*, template: str, start: int) -> dict[int, frozenset[str]]:
    return {start + offset: iupac_bases(symbol) for offset, symbol in enumerate(template)}


def _domains(
    *,
    coordinates: set[int],
    maps: tuple[dict[int, frozenset[str]], ...],
) -> tuple[RelativeBaseDomain, ...]:
    rows: list[RelativeBaseDomain] = []
    for coordinate in sorted(coordinates):
        allowed = set(_ALL_BASES)
        for domain_map in maps:
            if coordinate in domain_map:
                allowed &= domain_map[coordinate]
        rows.append(
            RelativeBaseDomain(
                relative_coordinate=coordinate,
                allowed_bases=tuple(base for base in _BASES if base in allowed),
            )
        )
    return tuple(rows)


def evaluate_basal_processing_geometry(
    agent: NickingAgent,
    *,
    release: BasalReleaseGeometry,
    request: BasalProcessingGeometryRequest,
) -> BasalProcessingGeometryFeasibility:
    """Evaluate one nicking agent against exact release and caller domains."""
    geometry = orient_nick_geometry(
        motif_top_5to3=agent.motif_top_5to3,
        native_nicked_strand=agent.nicked_strand,
        cut_offset=agent.cut_offset,
        target_strand=request.terminal_nicked_strand,
    )
    orientation = geometry.orientation
    motif = geometry.motif_top_5to3
    cut_offset = geometry.cut_offset
    nick_boundary = 4
    nick_site_start = nick_boundary - cut_offset
    nick_site_end = nick_site_start + len(motif)

    release_map = _motif_map(
        motif=release.oriented_motif_top_5to3,
        start=release.site_start,
    )
    nick_map = _motif_map(motif=motif, start=nick_site_start)
    scar_map = _template_map(template=request.retained_scar_template, start=0)
    post_map = _template_map(template=request.post_nick_template, start=nick_boundary)
    coordinates = set(release_map) | set(nick_map) | set(scar_map) | set(post_map)
    resolved = _domains(
        coordinates=coordinates,
        maps=(release_map, nick_map, scar_map, post_map),
    )
    by_coordinate = {domain.relative_coordinate: domain for domain in resolved}
    retained = tuple(by_coordinate[coordinate] for coordinate in range(4))
    post = tuple(
        by_coordinate[coordinate]
        for coordinate in range(nick_boundary, nick_boundary + len(request.post_nick_template))
    )

    blockers: list[BasalProcessingGeometryBlocker] = []
    if any(
        not (release_map[coordinate] & nick_map[coordinate])
        for coordinate in set(release_map) & set(nick_map)
    ):
        blockers.append(BasalProcessingGeometryBlocker.RELEASE_NICK_DOMAIN_CONFLICT)
    if any(not domain.allowed_bases for domain in retained):
        blockers.append(BasalProcessingGeometryBlocker.RETAINED_SCAR_DOMAIN_EMPTY)

    post_coordinates = set(post_map)
    process_post_coordinates = {
        coordinate for coordinate in set(release_map) | set(nick_map) if coordinate >= nick_boundary
    }
    if any(not by_coordinate[coordinate].allowed_bases for coordinate in post_coordinates):
        blockers.append(BasalProcessingGeometryBlocker.POST_NICK_DOMAIN_CONFLICT)
    if process_post_coordinates - post_coordinates:
        blockers.append(BasalProcessingGeometryBlocker.POST_NICK_DOMAIN_UNCOVERED)
    if request.post_nick_domain_mode == "preserve" and any(
        set(by_coordinate[coordinate].allowed_bases) != post_map[coordinate]
        and bool(by_coordinate[coordinate].allowed_bases)
        for coordinate in post_coordinates
    ):
        blockers.append(BasalProcessingGeometryBlocker.POST_NICK_DOMAIN_NARROWED)

    return BasalProcessingGeometryFeasibility(
        release_agent_id=release.release_agent_id,
        nicking_agent_id=agent.agent_id,
        orientation=orientation,
        oriented_motif_top_5to3=motif,
        nick_site_start=nick_site_start,
        nick_site_end=nick_site_end,
        nick_boundary=nick_boundary,
        nicked_strand=request.terminal_nicked_strand,
        resolved_domains=resolved,
        retained_scar_domains=retained,
        post_nick_domains=post,
        feasible_scar_count=prod(len(domain.allowed_bases) for domain in retained),
        blockers=tuple(blockers),
        compatible=not blockers,
    )


__all__ = [
    "evaluate_basal_processing_geometry",
    "resolve_basal_release_geometry",
]
