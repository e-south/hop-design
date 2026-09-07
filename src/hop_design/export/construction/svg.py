"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/svg.py

Dispatches typed construction projections to their publication-oriented SVG renderers.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalMinimumOverheadMatrixProjection,
    CompleteConstructionSummaryProjection,
    CompleteConstructionTrajectoryProjection,
    ConstructionNavigationProjection,
    ConstructionScientificProjection,
    FoldbackFeasibilityProjection,
    RetainedOverheadFrontierProjection,
    SourcePartitionCertificateProjection,
)

from .basal_svg import render_basal_matrix_svg, render_basal_projection_svg
from .complete_svg import render_complete_projection_svg
from .foldback_svg import render_foldback_projection_svg
from .navigation_svg import render_navigation_projection_svg
from .overhead_svg import render_retained_overhead_svg
from .source_partition_svg import render_source_partition_projection_svg
from .trajectory_svg import render_complete_trajectory_svg


def render_projection_svg(projection: ConstructionScientificProjection) -> bytes:
    """Render one scientific relation without molecular recomputation or ranking."""
    if isinstance(projection, CompleteConstructionSummaryProjection):
        return render_complete_projection_svg(projection)
    if isinstance(projection, ConstructionNavigationProjection):
        return render_navigation_projection_svg(projection)
    if isinstance(projection, CompleteConstructionTrajectoryProjection):
        return render_complete_trajectory_svg(projection)
    if isinstance(projection, SourcePartitionCertificateProjection):
        return render_source_partition_projection_svg(projection)
    if isinstance(projection, FoldbackFeasibilityProjection):
        return render_foldback_projection_svg(projection)
    if isinstance(projection, BasalFeasibilityProjection):
        return render_basal_projection_svg(projection)
    if isinstance(projection, BasalMinimumOverheadMatrixProjection):
        return render_basal_matrix_svg(projection)
    if isinstance(projection, RetainedOverheadFrontierProjection):
        return render_retained_overhead_svg(projection)
    raise TypeError(f"Unsupported scientific projection: {type(projection).__name__}")


__all__ = ["render_projection_svg"]
