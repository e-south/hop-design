"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/__init__.py

Defines payload-centered construction contracts and discovery evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .accounting import (
    DigitalDesignStatus,
    ExperimentalEvidenceStatus,
    FailureReasonCount,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    NeighborhoodProvenance,
    OverheadLevelSummary,
    OverheadPosition,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    ProjectionInventoryItem,
    ProjectionInventoryStatus,
    RealizationGroup,
    RealizationGrouping,
    RetainedOverheadLedger,
    SearchCompletionStatus,
    SearchDisposition,
    SearchFeasibilityStatus,
    SearchTerminationReason,
)
from .bundle import ConstructionBundle
from .payload import (
    ConstructionEndpoint,
    FinalPayloadReference,
    LocalNeighborhoodFamily,
    PairState,
    PairStateException,
    PayloadSourceMap,
    PayloadSourceSegment,
    RouteFamily,
    SourceOrientation,
    validate_linear_source_map,
    validate_linear_source_payload,
)
from .projection import (
    ProjectionReference,
    grouped_realization_projection,
)
from .realization import (
    CompleteConstructionRealization,
    ConstructionExecution,
    FinalProductReference,
    LocalRealization,
)
from .request import (
    LocalNeighborhoodRequest,
    geometry_id,
    problem_id,
)
from .result import NeighborhoodDiscoveryResult
from .search import (
    BasalGeometryDomain,
    FoldbackGeometryDomain,
    FoldbackOverheadLevel,
    LocalGeometryDomain,
    NeighborhoodSearchPlan,
    SearchScope,
    SearchStopMode,
)
from .sequence_domain import SequenceDomainPartition
from .targets import (
    BasalPairAllowance,
    BasalPairClass,
    BasalPairingConstraint,
    BasalTarget,
    ConstructionConstraints,
    ConstructionPreferences,
    FoldbackTarget,
    LocalGeometryTarget,
    NickStrandSelection,
)

__all__ = [
    "BasalGeometryDomain",
    "BasalPairAllowance",
    "BasalPairClass",
    "BasalPairingConstraint",
    "BasalTarget",
    "CompleteConstructionRealization",
    "ConstructionBundle",
    "ConstructionConstraints",
    "ConstructionEndpoint",
    "ConstructionExecution",
    "ConstructionPreferences",
    "DigitalDesignStatus",
    "ExperimentalEvidenceStatus",
    "FailureReasonCount",
    "FinalPayloadReference",
    "FinalProductReference",
    "FoldbackGeometryDomain",
    "FoldbackOverheadLevel",
    "FoldbackTarget",
    "LocalGeometryDomain",
    "LocalGeometryTarget",
    "LocalNeighborhoodFamily",
    "LocalNeighborhoodRequest",
    "LocalRealization",
    "MethodResolutionStatus",
    "NeighborhoodClaimBoundary",
    "NeighborhoodDiscoveryResult",
    "NeighborhoodProvenance",
    "NeighborhoodSearchPlan",
    "NickStrandSelection",
    "OverheadLevelSummary",
    "OverheadPosition",
    "PairState",
    "PairStateException",
    "PayloadCompatibilityAccounting",
    "PayloadCompatibilityStatus",
    "PayloadSourceMap",
    "PayloadSourceSegment",
    "ProjectionInventoryItem",
    "ProjectionInventoryStatus",
    "ProjectionReference",
    "RealizationGroup",
    "RealizationGrouping",
    "RetainedOverheadLedger",
    "RouteFamily",
    "SearchCompletionStatus",
    "SearchDisposition",
    "SearchFeasibilityStatus",
    "SearchScope",
    "SearchStopMode",
    "SearchTerminationReason",
    "SequenceDomainPartition",
    "SourceOrientation",
    "geometry_id",
    "grouped_realization_projection",
    "problem_id",
    "validate_linear_source_map",
    "validate_linear_source_payload",
]
