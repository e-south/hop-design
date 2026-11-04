"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_preparation/route.py

Defines linear-source preparation and endpoint auxiliary material inputs.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from ..auxiliary import EndpointAuxiliaryPolicy
from ..auxiliary.policy import AdapterResolutionPolicy
from .policy import ConstrainedSourceSsdnaPolicy, SourceDuplexPreparationPolicy


class LinearSourceMaterializationSpec(HopModel):
    """Source preparation plus endpoint-dependent auxiliary resolution policy."""

    source_preparation: SourceDuplexPreparationPolicy
    endpoint_auxiliaries: EndpointAuxiliaryPolicy | None = None
    adapter_ligation: AdapterResolutionPolicy | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def validate_context_endpoint(self) -> LinearSourceMaterializationSpec:
        if (
            isinstance(self.source_preparation.source_ssdna, ConstrainedSourceSsdnaPolicy)
            and self.endpoint_auxiliaries is None
            and self.adapter_ligation is None
        ):
            raise ValueError("Upstream context search requires a basal-bearing endpoint.")
        if self.endpoint_auxiliaries is not None and self.adapter_ligation is not None:
            raise ValueError(
                "Declare either adapter ligation or PCR endpoint auxiliaries, not both."
            )
        return self


__all__ = ["LinearSourceMaterializationSpec"]
