"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/use.py

Defines contextual uses of content-addressed construction materials.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import _content_id

from .spec import MaterialResolutionMode


class MaterialRouteEntry(StrEnum):
    """How one material use enters the modeled molecular route."""

    REQUIRED_EXTERNAL = "required_external"
    MODELED_PRODUCT = "modeled_product"


class MaterialUseRole(StrEnum):
    """Closed contextual roles in the linear-source route family."""

    SOURCE_SSDNA = "source_ssdna"
    SOURCE_MATERIALIZATION_FORWARD_PRIMER = "source_materialization_forward_primer"
    SOURCE_MATERIALIZATION_REVERSE_PRIMER = "source_materialization_reverse_primer"
    PREPARED_SOURCE_REFERENCE = "prepared_source_reference"
    PREPARED_SOURCE_COMPLEMENT = "prepared_source_complement"
    LIGATION_ADAPTER = "ligation_adapter"
    ENDPOINT_FORWARD_PRIMER = "endpoint_forward_primer"
    ENDPOINT_REVERSE_PRIMER = "endpoint_reverse_primer"


class MaterialUse(HopModel):
    """One contextual route use of an exact molecular material."""

    use_id: str = Field(pattern=r"^hop:material-use/[0-9a-f]{64}@1$")
    material_id: str = Field(pattern=r"^hop:construction-material/[0-9a-f]{64}@1$")
    role: MaterialUseRole
    specification_resolution_mode: MaterialResolutionMode
    route_entry: MaterialRouteEntry

    @classmethod
    def create(cls, **content: object) -> MaterialUse:
        draft = cls.model_construct(use_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"use_id"})
        return cls.model_validate({"use_id": _content_id("material-use", 1, seed), **content})

    @model_validator(mode="after")
    def validate_identity(self) -> MaterialUse:
        content = self.model_dump(mode="json", exclude={"use_id"})
        if self.use_id != _content_id("material-use", 1, content):
            raise ValueError("Material-use identity must seal material, role, and route entry.")
        return self


__all__ = ["MaterialRouteEntry", "MaterialUse", "MaterialUseRole"]
