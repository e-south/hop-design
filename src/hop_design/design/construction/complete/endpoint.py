"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/endpoint.py

Materializes one exact complete-construction endpoint from admitted local authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    MaterializedConstructionRealization,
)
from hop_design.models.construction.complete.evaluation import (
    CombinationEvaluation,
    CompositionRejectionCode,
)
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)

from .direct import direct_realization
from .pcr_endpoint import pcr_realization


def materialize_endpoint(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord | None,
    foldback_result: FoldbackNeighborhoodDiscoveryResult,
    basal_result: BasalNeighborhoodDiscoveryResult | None,
    evaluation: CombinationEvaluation,
) -> MaterializedConstructionRealization | CompositionRejectionCode:
    """Materialize the endpoint declared by one evaluated construction request."""
    if request.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
        return direct_realization(
            request,
            foldback=foldback,
            basal=basal,
            foldback_result=foldback_result,
            basal_result=basal_result,
            evaluation=evaluation,
        )
    if basal is None or basal_result is None:
        raise ValueError("PCR composition requires one exact basal authority.")
    return pcr_realization(
        request,
        foldback=foldback,
        basal=basal,
        foldback_result=foldback_result,
        basal_result=basal_result,
        evaluation=evaluation,
    )


__all__ = ["materialize_endpoint"]
