"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/selection.py

Defines a strict reference to one accepted complete-construction realization.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel


class ConstructionSelectionRecord(HopModel):
    """Non-authoritative reference to one accepted realization in one result."""

    schema_id: Literal["hop.construction-selection/v1"] = Field(
        default="hop.construction-selection/v1",
        alias="schema",
    )
    source_result_id: str = Field(pattern=r"^hop:construction-space-result/[0-9a-f]{64}@1$")
    materialized_realization_id: str = Field(
        pattern=r"^hop:materialized-construction/[0-9a-f]{64}@1$"
    )


__all__ = ["ConstructionSelectionRecord"]
