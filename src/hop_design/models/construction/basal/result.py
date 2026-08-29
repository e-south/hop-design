"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal/result.py

Defines the lossless relation between basal discovery and exact route records.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction import NeighborhoodDiscoveryResult

from .realization import BasalRealizationRecord


class BasalNeighborhoodDiscoveryResult(HopModel):
    """Shared discovery authority plus lossless exact basal route records."""

    discovery: NeighborhoodDiscoveryResult
    realizations: tuple[BasalRealizationRecord, ...]

    @model_validator(mode="after")
    def validate_relation(self) -> BasalNeighborhoodDiscoveryResult:
        discovery_ids = tuple(item.local_realization_id for item in self.discovery.realizations)
        detail_ids = tuple(
            item.local_realization.local_realization_id for item in self.realizations
        )
        if discovery_ids != detail_ids:
            raise ValueError("Basal records must preserve every discovery realization in order.")
        if any(
            item.projection.endpoint is not self.discovery.request.endpoint
            for item in self.realizations
        ):
            raise ValueError("Every basal projection must use the requested endpoint.")
        return self
