"""Bounded composition of basal candidates and terminal process geometry."""

from __future__ import annotations

from itertools import islice, product
from typing import Literal

from hop_design.models.coordinates import Boundary
from hop_design.models.discovery.basal_candidates import BasalCandidateSearchResult
from hop_design.models.discovery.basal_processing import BasalProcessingGeometrySearchResult
from hop_design.models.discovery.basal_routes import (
    BasalProcessingRouteCandidate,
    BasalProcessingRouteSearchLimits,
    BasalProcessingRouteSearchResult,
    BasalProcessingRouteTruncation,
    basal_processing_route_feasibility,
    basal_processing_route_id,
)
from hop_design.models.junction import Strand
from hop_design.models.strand_state import NickEvent


def search_basal_processing_routes(
    *,
    basal_candidates: BasalCandidateSearchResult,
    processing_geometries: BasalProcessingGeometrySearchResult,
    limits: BasalProcessingRouteSearchLimits,
) -> BasalProcessingRouteSearchResult:
    """Join exact basal pairs to compatible terminal process geometries."""
    available_pair_count = len(basal_candidates.hits) * len(processing_geometries.hits)
    examined = tuple(
        islice(
            product(basal_candidates.hits, processing_geometries.hits),
            limits.max_search_nodes,
        )
    )
    feasibility = tuple(
        basal_processing_route_feasibility(
            release=processing_geometries.release,
            basal_candidate=basal,
            processing_geometry=geometry,
        )
        for basal, geometry in examined
    )
    pair_by_ids = {
        (basal.candidate_id, geometry.candidate_id): (basal, geometry)
        for basal, geometry in examined
    }
    compatible = tuple(row for row in feasibility if row.compatible)
    returned = compatible[: limits.max_hits]
    hits = []
    for rank, row in enumerate(returned, start=1):
        basal, geometry = pair_by_ids[(row.basal_candidate_id, row.processing_geometry_id)]
        hits.append(
            BasalProcessingRouteCandidate(
                route_id=basal_processing_route_id(
                    release=processing_geometries.release,
                    basal_candidate=basal,
                    processing_geometry=geometry,
                ),
                rank=rank,
                release=processing_geometries.release,
                basal_candidate=basal,
                processing_geometry=geometry,
                feasibility=row,
                terminal_nick=NickEvent(
                    boundary=Boundary(offset=geometry.nick_boundary),
                    strand=geometry.nicked_strand,
                ),
                surviving_strand=(
                    Strand.BOTTOM if geometry.nicked_strand is Strand.TOP else Strand.TOP
                ),
            )
        )

    truncated_by: list[BasalProcessingRouteTruncation] = []
    if basal_candidates.status == "truncated":
        truncated_by.append("basal_candidates")
    if processing_geometries.status == "truncated":
        truncated_by.append("processing_geometries")
    if len(examined) < available_pair_count:
        truncated_by.append("max_search_nodes")
    if len(compatible) > limits.max_hits:
        truncated_by.append("max_hits")
    if truncated_by:
        status: Literal["complete", "infeasible", "truncated"] = "truncated"
    elif hits:
        status = "complete"
    else:
        status = "infeasible"
    return BasalProcessingRouteSearchResult(
        status=status,
        basal_candidates=basal_candidates,
        processing_geometries=processing_geometries,
        limits=limits,
        hits=tuple(hits),
        feasibility=feasibility,
        available_pair_count=available_pair_count,
        search_nodes_examined=len(examined),
        observed_hit_count=len(compatible),
        truncated_by=tuple(truncated_by),
    )


__all__ = ["search_basal_processing_routes"]
