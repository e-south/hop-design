"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/verification.py

Replays local scientific projections against their detailed result authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalMinimumOverheadMatrixProjection,
    FoldbackFeasibilityProjection,
    LocalScientificProjection,
    RetainedOverheadFrontierProjection,
)

from .basal import project_basal_feasibility, project_basal_minimum_overhead_matrix
from .foldback import project_foldback_feasibility
from .overhead import project_retained_overhead_frontier


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
    elif isinstance(projection, BasalMinimumOverheadMatrixProjection) and isinstance(
        source, BasalNeighborhoodDiscoveryResult
    ):
        expected = project_basal_minimum_overhead_matrix(source)
    elif isinstance(projection, RetainedOverheadFrontierProjection):
        expected = project_retained_overhead_frontier(source)
    else:
        raise ValueError("Local projection type does not match its detailed source result.")
    if projection != expected:
        raise ValueError("Local projection does not replay its detailed source result.")
    return projection
