"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/execution/records.py

Defines the finite execution plan and immutable batch inventory.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.construction import LocalNeighborhoodRequest

MAX_REQUESTS = 4096
MAX_BATCH_REQUESTS = 256
MAX_DOCUMENT_BYTES = 64 * 1024 * 1024


class ExecutionPlan(HopModel):
    schema_version: Literal["hop.local-neighborhood-execution/v1"] = Field(
        default="hop.local-neighborhood-execution/v1", alias="schema"
    )
    producer: dict[str, str]
    requests: tuple[LocalNeighborhoodRequest, ...] = Field(min_length=1, max_length=MAX_REQUESTS)


class BatchInventory(HopModel):
    schema_version: Literal["hop.local-neighborhood-batch/v1"] = Field(
        default="hop.local-neighborhood-batch/v1", alias="schema"
    )
    plan_digest: str
    start: int = Field(ge=0, lt=MAX_REQUESTS)
    result_digests: tuple[str, ...] = Field(min_length=1, max_length=MAX_BATCH_REQUESTS)
    compressed_digest: str


class CompletionRecord(HopModel):
    schema_version: Literal["hop.local-neighborhood-execution-completion/v1"] = Field(
        default="hop.local-neighborhood-execution-completion/v1", alias="schema"
    )
    plan_digest: str
    batch_digests: tuple[str, ...] = Field(min_length=1, max_length=MAX_REQUESTS)
