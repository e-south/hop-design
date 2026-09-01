"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/__init__.py

Exports typed, renderer-independent projections of local construction results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .complete import (
    CompleteConstructionSummaryProjection,
    CompleteConstructionSummaryRow,
)
from .local import (
    BasalFeasibilityProjection,
    BasalFeasibilityRow,
    FoldbackFeasibilityProjection,
    FoldbackFeasibilityRow,
    LocalScientificProjection,
    RelaxationFrontierProjection,
    RelaxationShellProjection,
)
from .navigation import (
    ConstructionNavigationAcceptedRoute,
    ConstructionNavigationGeometryGroup,
    ConstructionNavigationProjection,
)
from .trajectory import CompleteConstructionTrajectoryProjection

__all__ = [
    "BasalFeasibilityProjection",
    "BasalFeasibilityRow",
    "CompleteConstructionSummaryProjection",
    "CompleteConstructionSummaryRow",
    "CompleteConstructionTrajectoryProjection",
    "ConstructionNavigationAcceptedRoute",
    "ConstructionNavigationGeometryGroup",
    "ConstructionNavigationProjection",
    "FoldbackFeasibilityProjection",
    "FoldbackFeasibilityRow",
    "LocalScientificProjection",
    "RelaxationFrontierProjection",
    "RelaxationShellProjection",
]
