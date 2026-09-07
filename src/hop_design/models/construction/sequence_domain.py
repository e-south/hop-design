"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/sequence_domain.py

Defines deterministic partitions of exact local sequence enumeration.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import Field, model_validator

from hop_design.models.base import HopModel


class SequenceDomainPartition(HopModel):
    """One disjoint part of canonical exact sequence-solution enumeration."""

    part_count: int = Field(ge=2, le=256)
    part_index: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_index(self) -> SequenceDomainPartition:
        if self.part_index >= self.part_count:
            raise ValueError("sequence-partition part_index must be less than part_count.")
        return self


__all__ = ["SequenceDomainPartition"]
