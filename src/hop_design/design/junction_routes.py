"""Bounded composition of basal and cross-junction processing routes."""

from __future__ import annotations

from itertools import islice, product
from typing import Literal

from hop_design.models.coordinates import Boundary, Span
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
from hop_design.models.discovery.hairpin_routes import (
    HairpinJunctionRouteCandidate,
    HairpinJunctionRouteSearchLimits,
    HairpinJunctionRouteSearchResult,
    HairpinJunctionRouteTruncation,
    hairpin_junction_route_feasibility,
    hairpin_junction_route_id,
)
from hop_design.models.discovery.released_foldback import ReleasedFoldbackGeometryHit
from hop_design.models.discovery.released_foldback_candidates import (
    ReleasedFoldbackPrecursorCandidate,
    ReleasedFoldbackPrecursorSearchResult,
)
from hop_design.models.junction import Strand
from hop_design.models.physical import opposite_strand
from hop_design.models.strand_state import (
    NickEvent,
    ReleasedStrandState,
    ReleaseProjectionConstraints,
    ReleaseProjectionRequest,
    StrandExposureRoute,
)

from .processing import project_released_strand_state


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
    for canonical_ordinal, row in enumerate(returned, start=1):
        basal, geometry = pair_by_ids[(row.basal_candidate_id, row.processing_geometry_id)]
        hits.append(
            BasalProcessingRouteCandidate(
                route_id=basal_processing_route_id(
                    release=processing_geometries.release,
                    basal_candidate=basal,
                    processing_geometry=geometry,
                ),
                canonical_ordinal=canonical_ordinal,
                release=processing_geometries.release,
                basal_candidate=basal,
                processing_geometry=geometry,
                feasibility=row,
                terminal_nick=NickEvent(
                    boundary=Boundary(offset=geometry.nick_boundary),
                    strand=geometry.nicked_strand,
                ),
                surviving_strand=opposite_strand(geometry.nicked_strand),
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


def _project_exact_released_state(
    *,
    geometry: ReleasedFoldbackGeometryHit,
    precursor: ReleasedFoldbackPrecursorCandidate,
) -> ReleasedStrandState:
    release_cut = geometry.release_cut
    if release_cut is None:
        raise ValueError("A compatible released-foldback geometry must contain a release cut.")
    route = (
        StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK
        if geometry.nick.strand is Strand.TOP
        else StrandExposureRoute.TOP_ACTIVE_AFTER_BOTTOM_NICK
    )
    result = project_released_strand_state(
        ReleaseProjectionRequest(
            precursor_top_strand=precursor.precursor_sequence,
            origin=geometry.active_product_span.start,
            nick=geometry.nick,
            release_cut=release_cut,
            release_site_span=Span(
                start=Boundary(offset=geometry.release_site_start),
                end=Boundary(offset=geometry.release_site_end),
            ),
            route=route,
            constraints=ReleaseProjectionConstraints(
                require_release_site_downstream_of_nick=False,
                require_complete_downstream_separation=False,
            ),
        )
    )
    if result.projection is None:
        codes = ", ".join(item.code for item in result.report.diagnostics)
        raise ValueError(
            "A compatible exact released-foldback precursor failed state projection: " + codes
        )
    return result.projection


def search_hairpin_junction_routes(
    *,
    released_precursors: ReleasedFoldbackPrecursorSearchResult,
    basal_routes: BasalProcessingRouteSearchResult,
    limits: HairpinJunctionRouteSearchLimits,
) -> HairpinJunctionRouteSearchResult:
    """Join exact foldback release and basal processing on one surviving strand."""
    geometry = released_precursors.request.geometry
    available_pair_count = len(released_precursors.hits) * len(basal_routes.hits)
    examined = tuple(
        islice(
            product(released_precursors.hits, basal_routes.hits),
            limits.max_search_nodes,
        )
    )
    feasibility = tuple(
        hairpin_junction_route_feasibility(
            geometry=geometry,
            released_foldback_precursor=precursor,
            basal_route=basal_route,
        )
        for precursor, basal_route in examined
    )
    pairs_by_ids = {
        (precursor.candidate_id, basal_route.route_id): (precursor, basal_route)
        for precursor, basal_route in examined
    }
    compatible = tuple(row for row in feasibility if row.compatible)
    returned = compatible[: limits.max_hits]
    hits = []
    for canonical_ordinal, row in enumerate(returned, start=1):
        precursor, basal_route = pairs_by_ids[
            (row.released_foldback_precursor_id, row.basal_route_id)
        ]
        released_state = _project_exact_released_state(
            geometry=geometry,
            precursor=precursor,
        )
        hits.append(
            HairpinJunctionRouteCandidate(
                route_id=hairpin_junction_route_id(
                    geometry=geometry,
                    released_foldback_precursor=precursor,
                    basal_route=basal_route,
                ),
                canonical_ordinal=canonical_ordinal,
                released_foldback_geometry=geometry,
                released_foldback_precursor=precursor,
                released_state=released_state,
                basal_route=basal_route,
                feasibility=row,
            )
        )

    truncated_by: list[HairpinJunctionRouteTruncation] = []
    if released_precursors.status == "truncated":
        truncated_by.append("released_precursors")
    if basal_routes.status == "truncated":
        truncated_by.append("basal_routes")
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
    return HairpinJunctionRouteSearchResult(
        status=status,
        released_precursors=released_precursors,
        basal_routes=basal_routes,
        limits=limits,
        hits=tuple(hits),
        feasibility=feasibility,
        available_pair_count=available_pair_count,
        search_nodes_examined=len(examined),
        observed_hit_count=len(compatible),
        truncated_by=tuple(truncated_by),
    )


__all__ = ["search_basal_processing_routes", "search_hairpin_junction_routes"]
