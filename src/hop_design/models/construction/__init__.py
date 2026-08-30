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
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    ProjectionInventoryItem,
    ProjectionInventoryStatus,
    RealizationGroup,
    RealizationGrouping,
    RelaxationShellSummary,
    SearchCompletionStatus,
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
from .relaxation import (
    EnumerationPolicy,
    RelaxationCoordinate,
    RelaxationMode,
    RelaxationPolicy,
    geometry_coordinate_value,
    geometry_fixed_projection,
    geometry_with_coordinate_value,
)
from .request import (
    LocalNeighborhoodRequest,
    geometry_id,
    problem_id,
)
from .result import NeighborhoodDiscoveryResult
from .targets import (
    BasalNickStrand,
    BasalPairAllowance,
    BasalPairClass,
    BasalPairingConstraint,
    BasalTarget,
    ConstructionConstraints,
    ConstructionPreferences,
    EndGenerationRequest,
    FoldbackTarget,
    LocalGeometryTarget,
)

__all__ = [
    "BasalNickStrand",
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
    "EndGenerationRequest",
    "EnumerationPolicy",
    "ExperimentalEvidenceStatus",
    "FailureReasonCount",
    "FinalPayloadReference",
    "FinalProductReference",
    "FoldbackTarget",
    "LocalGeometryTarget",
    "LocalNeighborhoodFamily",
    "LocalNeighborhoodRequest",
    "LocalRealization",
    "MethodResolutionStatus",
    "NeighborhoodClaimBoundary",
    "NeighborhoodDiscoveryResult",
    "NeighborhoodProvenance",
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
    "RelaxationCoordinate",
    "RelaxationMode",
    "RelaxationPolicy",
    "RelaxationShellSummary",
    "RouteFamily",
    "SearchCompletionStatus",
    "SourceOrientation",
    "geometry_coordinate_value",
    "geometry_fixed_projection",
    "geometry_id",
    "geometry_with_coordinate_value",
    "grouped_realization_projection",
    "problem_id",
    "validate_linear_source_map",
    "validate_linear_source_payload",
]
