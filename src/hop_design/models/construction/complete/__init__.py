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
    LinearSourceMaterializationSpec,
    MaterialOrigin,
    PcrPrimer,
)
from .material_disposition import (
    EndpointMaterialOccurrence,
    MaterialRetentionDisposition,
    RouteMaterialDispositionSpan,
)
from .materials import derived_source_material_id
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
from .source_preparation import (
    SourceDuplexPreparationAuthority,
    derive_source_duplex_preparation,
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
    "DesignAuthorityReference",
    "DuplexFinalProductReference",
    "EndpointMaterialOccurrence",
    "EndpointSequenceFate",
    "EndpointSequenceFateSpan",
    "EndpointStrand",
    "ExactConstructionMaterial",
    "ExactStateRelation",
    "LinearSourceMaterializationSpec",
    "MaterialFunction",
    "MaterialFunctionSpan",
    "MaterialOrigin",
    "MaterialRetentionDisposition",
    "MaterializedConstructionRealization",
    "MaterializedFinalProduct",
    "PcrPrimer",
    "PrimerExtensionAuthority",
    "ReactionBoundaryMapping",
    "ReleaseSideRequirement",
    "RouteMaterialDispositionSpan",
    "SourceDuplexPreparationAuthority",
    "TypeIisReleaseRequest",
    "WholeRouteConstraints",
    "derive_source_duplex_preparation",
    "derived_source_material_id",
]
