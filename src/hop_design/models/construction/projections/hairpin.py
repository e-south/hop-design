"""An exact joined hairpin, its scaffold dimensions and separately staged release."""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field, model_validator

from hop_design.models.construction.hairpin_geometry import (
    HairpinArchitecture,
    LaterReleaseInterface,
)
from hop_design.models.construction.payload import _content_id


class HairpinPortraitProjection(HairpinArchitecture):
    """Non-authoritative portrait of a selected complete construction's hairpin."""

    schema_id: Literal["hop.hairpin-portrait/v1"] = Field(
        default="hop.hairpin-portrait/v1", alias="schema"
    )
    projection_id: str = Field(pattern=r"^hop:hairpin-portrait/[0-9a-f]{64}@1$")
    renderer_version: Literal["hairpin-portrait/1"] = "hairpin-portrait/1"
    source_result_id: str = Field(pattern=r"^hop:construction-space-result/[0-9a-f]{64}@1$")
    materialized_realization_id: str = Field(
        pattern=r"^hop:materialized-construction/[0-9a-f]{64}@1$"
    )

    @classmethod
    def create(cls, **content: object) -> HairpinPortraitProjection:
        draft = cls.model_construct(projection_id="", **cast(Any, content))
        return cls.model_validate({"projection_id": draft._expected_id(), **content})

    def _expected_id(self) -> str:
        return _content_id(
            "hairpin-portrait",
            1,
            self.model_dump(mode="json", by_alias=True, exclude={"projection_id"}),
        )

    @model_validator(mode="after")
    def validate_identity(self) -> HairpinPortraitProjection:
        if self.projection_id != self._expected_id():
            raise ValueError("Hairpin portrait identity must seal its full projected state.")
        return self


__all__ = ["HairpinArchitecture", "HairpinPortraitProjection", "LaterReleaseInterface"]
