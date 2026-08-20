"""Shared strict model policy."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HopModel(BaseModel):
    """Base contract that rejects coercion, mutation, and unknown fields."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        validate_by_alias=True,
        validate_by_name=True,
    )
