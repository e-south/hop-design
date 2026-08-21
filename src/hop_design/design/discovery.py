"""Bounded discovery over caller-supplied processing-agent geometry."""

from __future__ import annotations

from typing import Literal

from hop_design.kernel.discovery import evaluate_nicking_placement
from hop_design.models.catalog import ProcessingCatalog
from hop_design.models.discovery import (
    NickingPlacementHit,
    NickingPlacementSearchLimits,
    NickingPlacementSearchResult,
    NickingPlacementTarget,
    NickingPlacementTruncation,
)


def _hit_rank_key(hit: NickingPlacementHit) -> tuple[object, ...]:
    return (
        0 if hit.hit_kind == "exact" else 1,
        hit.boundary_displacement.value,
        hit.required_precursor.value,
        hit.required_turn.value,
        hit.agent_id,
        hit.orientation,
    )


def search_nicking_placements(
    *,
    catalog: ProcessingCatalog,
    target: NickingPlacementTarget,
    limits: NickingPlacementSearchLimits,
) -> NickingPlacementSearchResult:
    """Find exact or nearest nicking geometries without constructing sequences."""
    agents = sorted(catalog.nicking_agents, key=lambda agent: agent.agent_id)
    candidate_space_size = len(agents)
    examined = agents[: limits.max_search_nodes]
    feasibility = []
    observed_hits = []
    for agent in examined:
        row, hit = evaluate_nicking_placement(agent, target=target)
        feasibility.append(row)
        if hit is not None:
            observed_hits.append(hit)

    ordered_hits = sorted(observed_hits, key=_hit_rank_key)
    returned_hits = ordered_hits[: limits.max_hits]
    truncated_by: list[NickingPlacementTruncation] = []
    if len(examined) < candidate_space_size:
        truncated_by.append("max_search_nodes")
    if len(returned_hits) < len(ordered_hits):
        truncated_by.append("max_hits")

    if truncated_by:
        status: Literal["complete", "infeasible", "truncated"] = "truncated"
    elif returned_hits:
        status = "complete"
    else:
        status = "infeasible"
    return NickingPlacementSearchResult(
        status=status,
        catalog_id=catalog.catalog_id,
        target=target,
        hits=tuple(returned_hits),
        feasibility=tuple(feasibility),
        candidate_space_size=candidate_space_size,
        search_nodes_examined=len(examined),
        observed_hit_count=len(ordered_hits),
        truncated_by=tuple(truncated_by),
    )


__all__ = ["search_nicking_placements"]
