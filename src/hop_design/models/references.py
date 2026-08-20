"""Neutral identifiers and caller-owned external record links."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from hop_design.models.base import HopModel

ReferenceId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9+.-]*:[^\s]+$")]


class ExternalRef(HopModel):
    """A neutral link to a record owned by another system."""

    system: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    id: str = Field(min_length=1)


__all__ = ["ExternalRef", "ReferenceId"]
