"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/overhead.py

Builds retained-overhead coverage projections for local construction results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal, overload

from hop_design.models.construction import grouped_realization_projection
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.projections import (
    RetainedOverheadFrontierProjection,
    RetainedOverheadLevelProjection,
)
from hop_design.models.construction.projections.basal import (
    BASAL_PART_PROJECTION_RENDERER_VERSION,
    BASAL_PROJECTION_RENDERER_VERSION,
)
from hop_design.models.construction.projections.overhead import (
    FOLDBACK_OVERHEAD_RENDERER_VERSION,
    FOLDBACK_PART_OVERHEAD_RENDERER_VERSION,
)


@overload
def project_retained_overhead_frontier(
    result: FoldbackNeighborhoodDiscoveryResult,
) -> RetainedOverheadFrontierProjection: ...


@overload
def project_retained_overhead_frontier(
    result: BasalNeighborhoodDiscoveryResult,
) -> RetainedOverheadFrontierProjection: ...


def project_retained_overhead_frontier(
    result: FoldbackNeighborhoodDiscoveryResult | BasalNeighborhoodDiscoveryResult,
) -> RetainedOverheadFrontierProjection:
    """Project exact retained-overhead coverage without recomputing discovery."""
    if isinstance(result, FoldbackNeighborhoodDiscoveryResult):
        neighborhood = result.neighborhood
        source_result_id = result.result_id
        family: Literal["foldback", "basal"] = "foldback"
        partition = neighborhood.request.search.sequence_partition
        renderer_version = (
            FOLDBACK_PART_OVERHEAD_RENDERER_VERSION
            if partition is not None
            else FOLDBACK_OVERHEAD_RENDERER_VERSION
        )
        schema: Literal[
            "hop.foldback-overhead-frontier/v1",
            "hop.foldback-overhead-frontier/v2",
            "hop.basal-overhead-frontier/v1",
            "hop.basal-overhead-frontier/v2",
        ] = (
            "hop.foldback-overhead-frontier/v2"
            if partition is not None
            else "hop.foldback-overhead-frontier/v1"
        )
    else:
        neighborhood = result.discovery
        source_result_id = result.result_id
        family = "basal"
        partition = neighborhood.request.search.sequence_partition
        renderer_version = (
            BASAL_PART_PROJECTION_RENDERER_VERSION
            if partition is not None
            else BASAL_PROJECTION_RENDERER_VERSION
        )
        schema = (
            "hop.basal-overhead-frontier/v2"
            if partition is not None
            else "hop.basal-overhead-frontier/v1"
        )
    realization_ids = tuple(item.local_realization_id for item in neighborhood.realizations)
    reference = grouped_realization_projection(
        result_id=source_result_id,
        projection_schema=schema,
        renderer_version=renderer_version,
        realization_ids=realization_ids,
        groups=neighborhood.achieved_geometry_groups,
    )
    return RetainedOverheadFrontierProjection(
        schema=schema,
        projection_reference=reference,
        projection_id=reference.projection_id,
        source_result_id=reference.result_id,
        renderer_version=reference.renderer_version,
        provenance=neighborhood.provenance,
        claim_boundary=neighborhood.claim_boundary,
        problem_id=neighborhood.problem_id,
        family=family,
        endpoint=neighborhood.request.endpoint,
        disposition=neighborhood.disposition,
        sequence_partition=partition,
        levels=tuple(
            RetainedOverheadLevelProjection(
                retained_overhead_nt=level.retained_overhead_nt,
                status="complete" if level.complete else "partial",
                candidate_count=level.candidate_count,
                realization_count=len(level.realization_ids),
                realization_ids=level.realization_ids,
                rejected_count=level.rejected_count,
                failure_reasons=level.failure_reasons,
            )
            for level in neighborhood.overhead_levels
        ),
    )
