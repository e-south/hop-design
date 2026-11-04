"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/foldback.py

Builds neutral feasibility projections for foldback-neighborhood results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal, cast

from hop_design.models.construction import (
    FoldbackTarget,
    SourceOrientation,
    grouped_realization_projection,
)
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)
from hop_design.models.construction.projections import (
    FoldbackFeasibilityProjection,
    FoldbackFeasibilityRow,
)
from hop_design.models.construction.projections.foldback import (
    FOLDBACK_FEASIBILITY_RENDERER_VERSION,
    FOLDBACK_PART_FEASIBILITY_RENDERER_VERSION,
)


def _physical_row(item: FoldbackLocalRealization) -> FoldbackFeasibilityRow:
    """Measure source boundaries and retained pairing from replayed molecular facts."""
    target = cast(FoldbackTarget, item.local_realization.achieved_geometry)
    segment = item.payload_source_map.segments[0]
    payload_boundary = (
        segment.source_span.end.offset
        if segment.orientation is SourceOrientation.FORWARD
        else segment.source_span.start.offset
    )
    positions = tuple(position.position for position in item.retained_overhead.positions)
    return FoldbackFeasibilityRow(
        local_realization_id=item.local_realization.local_realization_id,
        foldback_realization_id=item.foldback_realization_id,
        program_kind=item.program_kind,
        nick_strand=item.foldback_nick.strand,
        source_orientation=segment.orientation,
        junction_offset_nt=target.junction_offset_nt,
        loop_length_nt=target.loop_length_nt,
        annealing_arm_length_bp=target.annealing_arm_length_bp,
        post_nick_arm_length_bp=sum(
            pair.left_strand_id == pair.right_strand_id for pair in item.annealing_pairs
        ),
        exposed_tail_length_nt=item.released_state.active_nick_boundary.offset,
        source_extension_length_nt=abs(item.terminus.boundary.offset - payload_boundary),
        retained_foldback_length_nt=len(positions),
        source_payload_boundary=payload_boundary,
        source_nick_boundary=item.foldback_nick.boundary.offset,
        source_terminus_boundary=item.terminus.boundary.offset,
        retained_foldback_start=min(positions),
        retained_foldback_end=max(positions) + 1,
        retained_overhead_nt=item.retained_overhead.retained_overhead_nt,
        transient_construction_nt=item.transient_construction_nt,
    )


def project_foldback_feasibility(
    result: FoldbackNeighborhoodDiscoveryResult,
) -> FoldbackFeasibilityProjection:
    """Project every exact foldback realization without ranking or selection."""
    neighborhood = result.neighborhood
    rows = tuple(_physical_row(item) for item in result.realizations)
    partition = neighborhood.request.search.sequence_partition
    schema: Literal[
        "hop.foldback-feasibility-landscape/v5",
        "hop.foldback-feasibility-landscape/v6",
    ] = (
        "hop.foldback-feasibility-landscape/v6"
        if partition is not None
        else "hop.foldback-feasibility-landscape/v5"
    )
    renderer_version = (
        FOLDBACK_PART_FEASIBILITY_RENDERER_VERSION
        if partition is not None
        else FOLDBACK_FEASIBILITY_RENDERER_VERSION
    )
    realization_ids = tuple(row.local_realization_id for row in rows)
    reference = grouped_realization_projection(
        result_id=result.result_id,
        projection_schema=schema,
        renderer_version=renderer_version,
        realization_ids=realization_ids,
        groups=neighborhood.achieved_geometry_groups,
    )
    return FoldbackFeasibilityProjection(
        schema=schema,
        projection_reference=reference,
        projection_id=reference.projection_id,
        source_result_id=reference.result_id,
        renderer_version=reference.renderer_version,
        provenance=neighborhood.provenance,
        claim_boundary=neighborhood.claim_boundary,
        problem_id=neighborhood.problem_id,
        endpoint=neighborhood.request.endpoint,
        disposition=neighborhood.disposition,
        sequence_partition=partition,
        realization_count=len(rows),
        rejected_count=neighborhood.rejected_count,
        realizations=rows,
    )
