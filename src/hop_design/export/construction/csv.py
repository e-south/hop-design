"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/csv.py

Dispatches typed construction projections to deterministic tidy CSV encoders.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import io

from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalMinimumOverheadMatrixProjection,
    CompleteConstructionSummaryProjection,
    ConstructionNavigationProjection,
    FoldbackFeasibilityProjection,
    RetainedOverheadFrontierProjection,
    SourcePartitionCertificateProjection,
    TabularConstructionProjection,
)

from .complete_csv import write_complete_projection
from .local_csv import (
    write_basal_matrix_projection,
    write_basal_projection,
    write_foldback_projection,
    write_retained_overhead_projection,
)
from .navigation_csv import render_navigation_projection_csv
from .source_partition_csv import render_source_partition_projection_csv


def render_projection_csv(projection: TabularConstructionProjection) -> bytes:
    """Render one projection with repeated context and lossless exact membership."""
    if isinstance(projection, ConstructionNavigationProjection):
        return render_navigation_projection_csv(projection)
    if isinstance(projection, SourcePartitionCertificateProjection):
        return render_source_partition_projection_csv(projection)
    buffer = io.StringIO(newline="")
    if isinstance(projection, CompleteConstructionSummaryProjection):
        write_complete_projection(buffer, projection)
    elif isinstance(projection, FoldbackFeasibilityProjection):
        write_foldback_projection(buffer, projection)
    elif isinstance(projection, BasalFeasibilityProjection):
        write_basal_projection(buffer, projection)
    elif isinstance(projection, BasalMinimumOverheadMatrixProjection):
        write_basal_matrix_projection(buffer, projection)
    elif isinstance(projection, RetainedOverheadFrontierProjection):
        write_retained_overhead_projection(buffer, projection)
    else:  # pragma: no cover - strict union protects public callers
        raise TypeError(f"Unsupported scientific projection: {type(projection).__name__}")
    return buffer.getvalue().encode("utf-8")


__all__ = ["render_projection_csv"]
