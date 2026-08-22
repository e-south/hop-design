"""Pure replay authority for released-foldback sequence-domain geometry."""

from __future__ import annotations

from collections.abc import Iterator
from math import prod

from hop_design.models.catalog import (
    NickingAgent,
    ProcessingCatalog,
    ReleaseAgent,
    SiteOrientation,
)
from hop_design.models.coordinates import Boundary, NucleotideCount, Span
from hop_design.models.discovery.released_foldback import (
    ExactBase,
    FoldbackPairingDomain,
    ReleasedFoldbackBaseDomain,
    ReleasedFoldbackGeometryBlocker,
    ReleasedFoldbackGeometryFeasibility,
    ReleasedFoldbackGeometryRequest,
    WatsonCrickPair,
)
from hop_design.models.junction import Strand
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac
from hop_design.models.strand_state import DuplexCut, NickEvent, StrandExposureRoute

_BASES: tuple[ExactBase, ...] = ("A", "C", "G", "T")
_WATSON_CRICK_PAIRS: tuple[WatsonCrickPair, ...] = ("AT", "CG", "GC", "TA")


def _expected_nicked_strand(route: StrandExposureRoute) -> Strand:
    return (
        Strand.TOP if route is StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK else Strand.BOTTOM
    )


def _nick_geometry(
    agent: NickingAgent,
    *,
    target_strand: Strand,
) -> tuple[SiteOrientation, str, int]:
    if agent.nicked_strand is target_strand:
        return SiteOrientation.FORWARD, agent.motif_top_5to3, agent.cut_offset
    return (
        SiteOrientation.REVERSE,
        reverse_complement_iupac(agent.motif_top_5to3),
        len(agent.motif_top_5to3) - agent.cut_offset,
    )


def _release_geometry(
    agent: ReleaseAgent,
    *,
    orientation: SiteOrientation,
) -> tuple[str, int, int]:
    if orientation is SiteOrientation.FORWARD:
        return agent.motif_top_5to3, agent.top_cut_offset, agent.bottom_cut_offset
    motif_nt = len(agent.motif_top_5to3)
    return (
        reverse_complement_iupac(agent.motif_top_5to3),
        motif_nt - agent.bottom_cut_offset,
        motif_nt - agent.top_cut_offset,
    )


def iter_released_foldback_boundaries(
    request: ReleasedFoldbackGeometryRequest,
) -> Iterator[Boundary]:
    """Return exact-first nonnegative nick boundaries inside the caller window."""
    target = request.target_nick_boundary.offset
    yield Boundary(offset=target)
    for displacement in range(1, request.max_boundary_displacement.value + 1):
        lower = target - displacement
        if lower >= 0:
            yield Boundary(offset=lower)
        yield Boundary(offset=target + displacement)


def released_foldback_boundary_count(request: ReleasedFoldbackGeometryRequest) -> int:
    """Return boundary-window cardinality without iterating through the window."""
    displacement = request.max_boundary_displacement.value
    return 1 + displacement + min(displacement, request.target_nick_boundary.offset)


def iter_released_foldback_geometry_nodes(
    *,
    catalog: ProcessingCatalog,
    request: ReleasedFoldbackGeometryRequest,
) -> Iterator[tuple[Boundary, NickingAgent, ReleaseAgent, SiteOrientation]]:
    """Yield the complete physical cross-product in exact-first stable order."""
    nicking_agents = tuple(sorted(catalog.nicking_agents, key=lambda row: row.agent_id))
    release_agents = tuple(sorted(catalog.release_agents, key=lambda row: row.agent_id))
    for boundary in iter_released_foldback_boundaries(request):
        for nicking_agent in nicking_agents:
            for release_agent in release_agents:
                yield boundary, nicking_agent, release_agent, SiteOrientation.FORWARD
                yield boundary, nicking_agent, release_agent, SiteOrientation.REVERSE


def released_foldback_candidate_space_size(
    *,
    catalog: ProcessingCatalog,
    request: ReleasedFoldbackGeometryRequest,
) -> int:
    """Return cardinality without materializing the search cross-product."""
    return (
        released_foldback_boundary_count(request)
        * len(catalog.nicking_agents)
        * len(catalog.release_agents)
        * 2
    )


def _process_domains(
    *,
    required_precursor: int,
    nick_motif: str,
    nick_start: int,
    release_motif: str,
    release_start: int,
) -> list[set[ExactBase]]:
    domains = [set(_BASES) for _ in range(required_precursor)]
    for motif, start in ((nick_motif, nick_start), (release_motif, release_start)):
        for offset, symbol in enumerate(motif):
            coordinate = start + offset
            if coordinate >= 0:
                domains[coordinate] &= iupac_bases(symbol)
    return domains


def _pairing_domains(
    *,
    domains: list[set[ExactBase]],
    nick_boundary: int,
    paired_tract: int,
    active_product_end: int,
) -> tuple[FoldbackPairingDomain, ...]:
    rows = []
    for offset in range(paired_tract):
        left = nick_boundary + offset
        right = active_product_end - 1 - offset
        allowed_pairs = tuple(
            pair
            for pair in _WATSON_CRICK_PAIRS
            if pair[0] in domains[left] and pair[1] in domains[right]
        )
        rows.append(
            FoldbackPairingDomain(
                left_coordinate=left,
                right_coordinate=right,
                allowed_pairs=allowed_pairs,
            )
        )
        domains[left] = {base for base in _BASES if any(pair[0] == base for pair in allowed_pairs)}
        domains[right] = {base for base in _BASES if any(pair[1] == base for pair in allowed_pairs)}
    return tuple(rows)


def evaluate_released_foldback_geometry(
    *,
    nicking_agent: NickingAgent,
    release_agent: ReleaseAgent,
    release_orientation: SiteOrientation,
    evaluated_nick_boundary: Boundary,
    request: ReleasedFoldbackGeometryRequest,
) -> ReleasedFoldbackGeometryFeasibility:
    """Evaluate one bounded agent-pair placement without selecting a sequence."""
    nicked_strand = _expected_nicked_strand(request.route)
    nick_orientation, nick_motif, nick_cut_offset = _nick_geometry(
        nicking_agent,
        target_strand=nicked_strand,
    )
    nick_boundary = evaluated_nick_boundary.offset
    nick_start = nick_boundary - nick_cut_offset
    nick_end = nick_start + len(nick_motif)
    active_end = nick_boundary + 2 * request.paired_tract.value + request.turn_length.value

    release_motif, release_top_offset, release_bottom_offset = _release_geometry(
        release_agent,
        orientation=release_orientation,
    )
    active_release_offset = (
        release_bottom_offset
        if request.route is StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK
        else release_top_offset
    )
    release_start = active_end - active_release_offset
    release_end = release_start + len(release_motif)
    release_top_cut = release_start + release_top_offset
    release_bottom_cut = release_start + release_bottom_offset
    required_precursor = max(
        active_end,
        nick_end,
        release_end,
        release_top_cut,
        release_bottom_cut,
    )

    blockers: list[ReleasedFoldbackGeometryBlocker] = []
    if nick_start < 0:
        blockers.append(ReleasedFoldbackGeometryBlocker.NICK_SITE_BEFORE_ORIGIN)
    if release_start < 0 or release_top_cut < 0 or release_bottom_cut < 0:
        blockers.append(ReleasedFoldbackGeometryBlocker.RELEASE_SITE_BEFORE_ORIGIN)
    if request.require_release_site_downstream_of_nick and release_start < nick_boundary:
        blockers.append(ReleasedFoldbackGeometryBlocker.RELEASE_SITE_NOT_DOWNSTREAM_OF_NICK)
    partner_release_cut = (
        release_top_cut
        if request.route is StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK
        else release_bottom_cut
    )
    if request.require_complete_downstream_separation and partner_release_cut < active_end:
        blockers.append(ReleasedFoldbackGeometryBlocker.INCOMPLETE_DOWNSTREAM_SEPARATION)

    domains = _process_domains(
        required_precursor=required_precursor,
        nick_motif=nick_motif,
        nick_start=nick_start,
        release_motif=release_motif,
        release_start=release_start,
    )
    process_conflict = any(not domain for domain in domains)
    if process_conflict:
        blockers.append(ReleasedFoldbackGeometryBlocker.PROCESSING_DOMAIN_CONFLICT)
    pairing = _pairing_domains(
        domains=domains,
        nick_boundary=nick_boundary,
        paired_tract=request.paired_tract.value,
        active_product_end=active_end,
    )
    if not process_conflict and any(not pair.allowed_pairs for pair in pairing):
        blockers.append(ReleasedFoldbackGeometryBlocker.FOLDBACK_PAIRING_DOMAIN_CONFLICT)

    paired_coordinates = {
        coordinate
        for pair in pairing
        for coordinate in (pair.left_coordinate, pair.right_coordinate)
    }
    sequence_count = prod(
        (
            *(len(pair.allowed_pairs) for pair in pairing),
            *(
                len(domain)
                for coordinate, domain in enumerate(domains)
                if coordinate not in paired_coordinates
            ),
        )
    )
    active_nick = (
        nick_boundary
        if request.route is StrandExposureRoute.TOP_ACTIVE_AFTER_BOTTOM_NICK
        else active_end - nick_boundary
    )
    return ReleasedFoldbackGeometryFeasibility(
        nicking_agent_id=nicking_agent.agent_id,
        release_agent_id=release_agent.agent_id,
        nick_orientation=nick_orientation,
        release_orientation=release_orientation,
        oriented_nick_motif_top_5to3=nick_motif,
        oriented_release_motif_top_5to3=release_motif,
        evaluated_nick_boundary=evaluated_nick_boundary,
        boundary_displacement=NucleotideCount(
            value=abs(nick_boundary - request.target_nick_boundary.offset)
        ),
        hit_kind=("exact" if nick_boundary == request.target_nick_boundary.offset else "nearest"),
        nick_site_start=nick_start,
        nick_site_end=nick_end,
        release_site_start=release_start,
        release_site_end=release_end,
        nick=NickEvent(boundary=evaluated_nick_boundary, strand=nicked_strand),
        release_cut=(
            DuplexCut(
                top=Boundary(offset=release_top_cut),
                bottom=Boundary(offset=release_bottom_cut),
            )
            if release_top_cut >= 0 and release_bottom_cut >= 0
            else None
        ),
        active_product_span=Span(
            start=Boundary(offset=0),
            end=Boundary(offset=active_end),
        ),
        active_nick_boundary=Boundary(offset=active_nick),
        required_precursor=NucleotideCount(value=required_precursor),
        resolved_domains=tuple(
            ReleasedFoldbackBaseDomain(
                coordinate=coordinate,
                allowed_bases=tuple(base for base in _BASES if base in domain),
            )
            for coordinate, domain in enumerate(domains)
        ),
        pairing_domains=pairing,
        candidate_sequence_count=sequence_count,
        blockers=tuple(blockers),
        compatible=not blockers,
    )


__all__ = [
    "evaluate_released_foldback_geometry",
    "iter_released_foldback_boundaries",
    "iter_released_foldback_geometry_nodes",
    "released_foldback_boundary_count",
    "released_foldback_candidate_space_size",
]
