"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/auxiliary/__init__.py

Exposes endpoint auxiliary-material policies and deterministic resolution.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from .policy import (
    ConstrainedAdapterPolicy,
    ConstrainedEndpointPrimerPolicy,
    DerivedAdapterPolicy,
    DerivedEndpointPrimerPolicy,
    EndpointAuxiliaryPolicy,
    FixedAdapterPolicy,
    FixedEndpointPrimerPolicy,
)
from .resolution import (
    EndpointAuxiliaryResolution,
    EndpointAuxiliaryResolutionError,
    EndpointAuxiliaryResolutionFailure,
    resolve_endpoint_auxiliaries,
)

__all__ = [
    "ConstrainedAdapterPolicy",
    "ConstrainedEndpointPrimerPolicy",
    "DerivedAdapterPolicy",
    "DerivedEndpointPrimerPolicy",
    "EndpointAuxiliaryPolicy",
    "EndpointAuxiliaryResolution",
    "EndpointAuxiliaryResolutionError",
    "EndpointAuxiliaryResolutionFailure",
    "FixedAdapterPolicy",
    "FixedEndpointPrimerPolicy",
    "resolve_endpoint_auxiliaries",
]
