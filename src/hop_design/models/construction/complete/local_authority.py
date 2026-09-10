"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/local_authority.py

Validates local discovery authority compatibility for complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import BasalGeometryDomain
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.sequence import iupac_bases

from .request import ConstructionDiscoveryRequest


def payload_space_contains(*, authored: str, exact: str) -> bool:
    """Return whether an exact payload belongs to an authored IUPAC domain."""
    return len(authored) == len(exact) and all(
        base in iupac_bases(symbol) for base, symbol in zip(exact, authored, strict=True)
    )


def validate_local_authority_compatibility(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackNeighborhoodDiscoveryResult,
    basal: BasalNeighborhoodDiscoveryResult | None,
) -> None:
    """Require payload, route family, and endpoint roles to match complete composition."""
    payload = request.payload.payload.sequence
    foldback_request = foldback.neighborhood.request
    if (
        not payload_space_contains(
            authored=foldback_request.payload.payload.sequence,
            exact=payload,
        )
        or foldback_request.route_family is not request.route_family
        or foldback_request.endpoint is not request.foldback_intermediate_endpoint
    ):
        raise ValueError("Foldback payload authority does not match the complete request.")
    if (request.basal_result_id is None) != (basal is None):
        raise ValueError("Basal authority presence must match the complete request.")
    if basal is None:
        return
    basal_request = basal.discovery.request
    if (
        not payload_space_contains(
            authored=basal_request.payload.payload.sequence,
            exact=payload,
        )
        or basal_request.route_family is not request.route_family
        or basal_request.endpoint is not request.endpoint
    ):
        raise ValueError("Basal payload authority does not match the complete request.")
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        release = request.release
        domain = basal_request.geometry_domain
        if not isinstance(domain, BasalGeometryDomain):
            raise ValueError("Basal authority requires a basal geometry domain.")
        future = domain.future_release
        if release is None or future is None:
            raise ValueError("Clone composition requires a future basal release obligation.")
        required = release.left if future.product_end == "left" else release.right
        if (
            future.orientation is not required.orientation
            or not future.permits_sequence(required.cohesive_end_sequence)
            or future.overhang_end is not required.overhang_end
        ):
            raise ValueError("Basal future release does not match the complete clone request.")


__all__ = ["payload_space_contains", "validate_local_authority_compatibility"]
