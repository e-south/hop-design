"""Exact parent-coordinate evidence for a released duplex insert."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Span
from hop_design.models.molecular_state import SequenceProjection


class ReleasedInsertEvidence(HopModel):
    """Keep the paired design core distinct from actual retained digest boundaries."""

    kind: Literal["released-insert/v1"] = "released-insert/v1"
    parent_state_id: str = Field(min_length=1)
    primary_parent_strand_id: str = Field(min_length=1)
    complementary_parent_strand_id: str = Field(min_length=1)
    design_parent_projection: SequenceProjection
    released_union_projection: SequenceProjection
    primary_parent_span: Span
    complementary_parent_span: Span


__all__ = ["ReleasedInsertEvidence"]
