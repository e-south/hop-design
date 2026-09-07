"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/__init__.py

Exports typed, renderer-independent projections of construction results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .basal import (
    BasalFeasibilityProjection,
    BasalFeasibilityRow,
    BasalMinimumOverheadCell,
    BasalMinimumOverheadMatrixProjection,
)
from .complete import (
    CompleteConstructionSummaryProjection,
    CompleteConstructionSummaryRow,
)
from .foldback import (
    FoldbackFeasibilityProjection,
    FoldbackFeasibilityRow,
)
from .local import (
    LocalScientificProjection,
)
from .navigation import (
    ConstructionNavigationAcceptedRoute,
    ConstructionNavigationGeometryGroup,
    ConstructionNavigationProjection,
)
from .overhead import (
    RetainedOverheadFrontierProjection,
    RetainedOverheadLevelProjection,
)
from .source_partition import SourcePartitionCertificateProjection
from .trajectory import CompleteConstructionTrajectoryProjection

type ConstructionScientificProjection = (
    LocalScientificProjection
    | CompleteConstructionSummaryProjection
    | CompleteConstructionTrajectoryProjection
    | ConstructionNavigationProjection
    | SourcePartitionCertificateProjection
)
type TabularConstructionProjection = (
    LocalScientificProjection
    | CompleteConstructionSummaryProjection
    | ConstructionNavigationProjection
    | SourcePartitionCertificateProjection
)

__all__ = [
    "BasalFeasibilityProjection",
    "BasalFeasibilityRow",
    "BasalMinimumOverheadCell",
    "BasalMinimumOverheadMatrixProjection",
    "CompleteConstructionSummaryProjection",
    "CompleteConstructionSummaryRow",
    "CompleteConstructionTrajectoryProjection",
    "ConstructionNavigationAcceptedRoute",
    "ConstructionNavigationGeometryGroup",
    "ConstructionNavigationProjection",
    "ConstructionScientificProjection",
    "FoldbackFeasibilityProjection",
    "FoldbackFeasibilityRow",
    "LocalScientificProjection",
    "RetainedOverheadFrontierProjection",
    "RetainedOverheadLevelProjection",
    "SourcePartitionCertificateProjection",
    "TabularConstructionProjection",
]
