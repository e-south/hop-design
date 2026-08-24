"""Pure nicking-agent placement geometry."""

from __future__ import annotations

from hop_design.models.catalog import NickingAgent
from hop_design.models.coordinates import Boundary, NucleotideCount, Span
from hop_design.models.discovery import (
    NickingPlacementBlocker,
    NickingPlacementFeasibility,
    NickingPlacementHit,
    NickingPlacementTarget,
)
from hop_design.models.physical import orient_nick_geometry
from hop_design.models.strand_state import NickEvent


def evaluate_nicking_placement(
    agent: NickingAgent,
    *,
    target: NickingPlacementTarget,
) -> tuple[NickingPlacementFeasibility, NickingPlacementHit | None]:
    """Evaluate one agent in the orientation that nicks the requested strand."""
    geometry = orient_nick_geometry(
        motif_top_5to3=agent.motif_top_5to3,
        native_nicked_strand=agent.nicked_strand,
        cut_offset=agent.cut_offset,
        target_strand=target.nicked_strand,
    )
    orientation = geometry.orientation
    oriented_motif = geometry.motif_top_5to3
    oriented_cut_offset = geometry.cut_offset
    target_boundary = target.nick_boundary.offset
    site_start = target_boundary - oriented_cut_offset
    site_end = site_start + len(oriented_motif)
    available_end = target_boundary + target.paired_tract.value + target.available_turn.value
    blockers: list[NickingPlacementBlocker] = []
    if site_start < 0:
        blockers.append("HOP-DISC-001")
    if site_end > available_end:
        blockers.append("HOP-DISC-002")

    extent_after_nick = len(oriented_motif) - oriented_cut_offset
    nearest_boundary: int | None = None
    if extent_after_nick <= target.paired_tract.value + target.available_turn.value:
        nearest_boundary = max(0, oriented_cut_offset)

    feasibility = NickingPlacementFeasibility(
        agent_id=agent.agent_id,
        orientation=orientation,
        oriented_motif_5to3=oriented_motif,
        site_start_at_target_boundary=site_start,
        site_end_at_target_boundary=site_end,
        exact_blockers=tuple(blockers),
        earliest_feasible_boundary=(
            Boundary(offset=nearest_boundary) if nearest_boundary is not None else None
        ),
    )
    if not blockers:
        boundary = target_boundary
    elif nearest_boundary is not None:
        boundary = nearest_boundary
    else:
        return feasibility, None

    placed_start = boundary - oriented_cut_offset
    placed_end = placed_start + len(oriented_motif)
    paired_end = boundary + target.paired_tract.value
    hit = NickingPlacementHit(
        hit_kind="exact" if boundary == target_boundary else "nearest",
        agent_id=agent.agent_id,
        orientation=orientation,
        oriented_motif_5to3=oriented_motif,
        site_span=Span(
            start=Boundary(offset=placed_start),
            end=Boundary(offset=placed_end),
        ),
        nick=NickEvent(boundary=Boundary(offset=boundary), strand=target.nicked_strand),
        boundary_displacement=NucleotideCount(value=abs(boundary - target_boundary)),
        required_precursor=NucleotideCount(value=max(paired_end, placed_end)),
        required_turn=NucleotideCount(value=max(0, placed_end - paired_end)),
    )
    return feasibility, hit


__all__ = ["evaluate_nicking_placement"]
