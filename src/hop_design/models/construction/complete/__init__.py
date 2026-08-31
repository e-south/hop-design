"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/__init__.py

Exposes bounded complete-route construction contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .accounting import (
    CompositionAccounting,
    CompositionEnumerationPolicy,
    CompositionPruningMode,
)
from .associations import ConstructionBondState
from .authority import (
    CompositionDisposition,
    CompositionDispositionStatus,
    CompositionMaterialAccounting,
    ConstructionCompositionExecution,
    ConstructionCompositionProvenance,
)
from .material import (
    ExactConstructionMaterial,
    MaterialResolutionMode,
    MaterialRouteEntry,
    MaterialUse,
    MaterialUseRole,
    PcrPrimer,
    ProducedMaterialBinding,
    construction_material_id,
)
from .material_disposition import (
    EndpointMaterialOccurrence,
    MaterialRetentionDisposition,
    RouteMaterialDispositionSpan,
)
from .pcr import (
    AdapterAnnealingAuthority,
    AdapterLigationAuthority,
    DuplexFinalProductReference,
    EndpointSequenceFate,
    EndpointSequenceFateSpan,
    EndpointStrand,
    MaterialFunction,
    MaterialFunctionSpan,
    PrimerExtensionAuthority,
)
from .product import MaterializedFinalProduct
from .program import (
    ConstructionProgram,
)
from .realization import MaterializedConstructionRealization
from .request import (
    ConstructionDiscoveryRequest,
    DesignAuthorityReference,
    ReleaseSideRequirement,
    TypeIisReleaseRequest,
    WholeRouteConstraints,
)
from .result import ConstructionSpaceResult
from .source_partition import SourcePartitionBinding
from .source_preparation import (
    ConstrainedPrimerPolicy,
    DerivedPrimerPolicy,
    DerivedSourceSsdnaPolicy,
    FixedPrimerPolicy,
    FixedSourceSsdnaPolicy,
    LinearSourceMaterializationSpec,
    SourceDuplexPreparationAuthority,
    SourceDuplexPreparationPolicy,
    SourcePreparationResolutionError,
    derive_source_duplex_preparation,
    resolve_source_duplex_preparation,
)
from .state import ConstructionState, ConstructionStatePhase
from .transition import (
    ConstructionTransition,
    ConstructionTransitionKind,
    ExactStateRelation,
    ReactionBoundaryMapping,
)

__all__ = [
    "AdapterAnnealingAuthority",
    "AdapterLigationAuthority",
    "CompositionAccounting",
    "CompositionDisposition",
    "CompositionDispositionStatus",
    "CompositionEnumerationPolicy",
    "CompositionMaterialAccounting",
    "CompositionPruningMode",
    "ConstrainedPrimerPolicy",
    "ConstructionBondState",
    "ConstructionCompositionExecution",
    "ConstructionCompositionProvenance",
    "ConstructionDiscoveryRequest",
    "ConstructionProgram",
    "ConstructionSpaceResult",
    "ConstructionState",
    "ConstructionStatePhase",
    "ConstructionTransition",
    "ConstructionTransitionKind",
    "DerivedPrimerPolicy",
    "DerivedSourceSsdnaPolicy",
    "DesignAuthorityReference",
    "DuplexFinalProductReference",
    "EndpointMaterialOccurrence",
    "EndpointSequenceFate",
    "EndpointSequenceFateSpan",
    "EndpointStrand",
    "ExactConstructionMaterial",
    "ExactStateRelation",
    "FixedPrimerPolicy",
    "FixedSourceSsdnaPolicy",
    "LinearSourceMaterializationSpec",
    "MaterialFunction",
    "MaterialFunctionSpan",
    "MaterialResolutionMode",
    "MaterialRetentionDisposition",
    "MaterialRouteEntry",
    "MaterialUse",
    "MaterialUseRole",
    "MaterializedConstructionRealization",
    "MaterializedFinalProduct",
    "PcrPrimer",
    "PrimerExtensionAuthority",
    "ProducedMaterialBinding",
    "ReactionBoundaryMapping",
    "ReleaseSideRequirement",
    "RouteMaterialDispositionSpan",
    "SourceDuplexPreparationAuthority",
    "SourceDuplexPreparationPolicy",
    "SourcePartitionBinding",
    "SourcePreparationResolutionError",
    "TypeIisReleaseRequest",
    "WholeRouteConstraints",
    "construction_material_id",
    "derive_source_duplex_preparation",
    "resolve_source_duplex_preparation",
]
