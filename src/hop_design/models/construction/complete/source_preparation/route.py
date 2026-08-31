"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_preparation/route.py

Defines linear-source preparation and endpoint auxiliary material inputs.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.base import HopModel

from ..auxiliary import EndpointAuxiliaryPolicy
from .policy import SourceDuplexPreparationPolicy


class LinearSourceMaterializationSpec(HopModel):
    """Source preparation plus endpoint-dependent auxiliary resolution policy."""

    source_preparation: SourceDuplexPreparationPolicy
    endpoint_auxiliaries: EndpointAuxiliaryPolicy | None = None


__all__ = ["LinearSourceMaterializationSpec"]
