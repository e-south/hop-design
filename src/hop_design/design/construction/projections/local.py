"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/local.py

Builds neutral scientific projections from validated local discovery results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal, cast, overload

from hop_design.models.construction import (
    BasalTarget,
    FoldbackTarget,
    grouped_realization_projection,
)
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalFeasibilityRow,
    FoldbackFeasibilityProjection,
    FoldbackFeasibilityRow,
    LocalScientificProjection,
    RetainedOverheadFrontierProjection,
    RetainedOverheadLevelProjection,
)
from hop_design.models.construction.projections.local import (
    BASAL_PART_PROJECTION_RENDERER_VERSION,
    BASAL_PROJECTION_RENDERER_VERSION,
    FOLDBACK_FEASIBILITY_RENDERER_VERSION,
    FOLDBACK_OVERHEAD_RENDERER_VERSION,
    FOLDBACK_PART_FEASIBILITY_RENDERER_VERSION,
    FOLDBACK_PART_OVERHEAD_RENDERER_VERSION,
)
from hop_design.models.junction import Strand


def project_foldback_feasibility(
    result: FoldbackNeighborhoodDiscoveryResult,
) -> FoldbackFeasibilityProjection:
    """Project every exact foldback realization without ranking or selection."""
    neighborhood = result.neighborhood
    rows = tuple(
        FoldbackFeasibilityRow(
            local_realization_id=item.local_realization.local_realization_id,
            foldback_realization_id=item.foldback_realization_id,
            program_kind=item.program_kind,
            nick_strand=item.foldback_nick.strand,
            source_orientation=item.payload_source_map.segments[0].orientation,
            junction_offset_nt=cast(
                FoldbackTarget, item.local_realization.achieved_geometry
            ).junction_offset_nt,
            loop_length_nt=cast(
                FoldbackTarget, item.local_realization.achieved_geometry
            ).loop_length_nt,
            annealing_arm_length_bp=cast(
                FoldbackTarget, item.local_realization.achieved_geometry
            ).annealing_arm_length_bp,
            retained_overhead_nt=item.retained_overhead.retained_overhead_nt,
            transient_construction_nt=item.transient_construction_nt,
        )
        for item in result.realizations
    )
    partition = neighborhood.request.search.sequence_partition
    schema: Literal[
        "hop.foldback-feasibility-landscape/v3",
        "hop.foldback-feasibility-landscape/v4",
    ] = (
        "hop.foldback-feasibility-landscape/v4"
        if partition is not None
        else "hop.foldback-feasibility-landscape/v3"
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


def project_basal_feasibility(
    result: BasalNeighborhoodDiscoveryResult,
) -> BasalFeasibilityProjection:
    """Project every exact basal realization with endpoint-dependent dimensions."""
    discovery = result.discovery
    rows = []
    for item in result.realizations:
        achieved = cast(BasalTarget, item.local_realization.achieved_geometry)
        pairing = item.projection.pairing_state
        rows.append(
            BasalFeasibilityRow(
                local_realization_id=item.local_realization.local_realization_id,
                basal_realization_id=item.basal_realization_id,
                retained_overhead_nt=item.retained_overhead.retained_overhead_nt,
                nick_strand=cast(Strand, achieved.nick_strand),
                nick_offset_nt=achieved.nick_offset_nt,
                pairing_pattern=pairing.pairing_pattern if pairing is not None else None,
                pairing_classes=(
                    tuple(pair.pair_class for pair in pairing.pairs) if pairing is not None else ()
                ),
                literal_pairs=pairing.pairs if pairing is not None else (),
                retained_nt=item.material_accounting.retained_nt,
                transient_nt=item.material_accounting.transient_nt,
                auxiliary_nt=item.material_accounting.auxiliary_nt,
            )
        )
    exact_rows = tuple(rows)
    partition = discovery.request.search.sequence_partition
    schema: Literal[
        "hop.basal-feasibility-landscape/v2",
        "hop.basal-feasibility-landscape/v3",
    ] = (
        "hop.basal-feasibility-landscape/v3"
        if partition is not None
        else "hop.basal-feasibility-landscape/v2"
    )
    renderer_version = (
        BASAL_PART_PROJECTION_RENDERER_VERSION
        if partition is not None
        else BASAL_PROJECTION_RENDERER_VERSION
    )
    reference = grouped_realization_projection(
        result_id=result.result_id,
        projection_schema=schema,
        renderer_version=renderer_version,
        realization_ids=tuple(row.local_realization_id for row in exact_rows),
        groups=discovery.achieved_geometry_groups,
    )
    return BasalFeasibilityProjection(
        schema=schema,
        projection_reference=reference,
        projection_id=reference.projection_id,
        source_result_id=reference.result_id,
        renderer_version=reference.renderer_version,
        provenance=discovery.provenance,
        claim_boundary=discovery.claim_boundary,
        problem_id=discovery.problem_id,
        endpoint=discovery.request.endpoint,
        disposition=discovery.disposition,
        sequence_partition=partition,
        realization_count=len(exact_rows),
        rejected_count=discovery.rejected_count,
        realizations=exact_rows,
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


def verify_local_projection(
    projection: LocalScientificProjection,
    source: FoldbackNeighborhoodDiscoveryResult | BasalNeighborhoodDiscoveryResult,
) -> LocalScientificProjection:
    """Replay one non-authoritative projection against its detailed source result."""
    expected: LocalScientificProjection
    if isinstance(projection, FoldbackFeasibilityProjection) and isinstance(
        source, FoldbackNeighborhoodDiscoveryResult
    ):
        expected = project_foldback_feasibility(source)
    elif isinstance(projection, BasalFeasibilityProjection) and isinstance(
        source, BasalNeighborhoodDiscoveryResult
    ):
        expected = project_basal_feasibility(source)
    elif isinstance(projection, RetainedOverheadFrontierProjection):
        expected = project_retained_overhead_frontier(source)
    else:
        raise ValueError("Local projection type does not match its detailed source result.")
    if projection != expected:
        raise ValueError("Local projection does not replay its detailed source result.")
    return projection
