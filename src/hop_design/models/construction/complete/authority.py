"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/authority.py

Defines complete-construction execution, provenance, and material accounting.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import _content_id

from .accounting import CompositionEnumerationPolicy
from .evaluation import CompositionRejectionCode


class ConstructionCompositionExecution(HopModel):
    """Replay identity for one bounded complete-route composition."""

    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    hop_version: str
    route_implementation_version: Literal["complete-construction/5"] = "complete-construction/5"
    enumeration: CompositionEnumerationPolicy
    environment: dict[str, str] = Field(default_factory=dict)

    @property
    def execution_id(self) -> str:
        """Return content identity over replay-relevant execution facts."""
        return _content_id("construction-execution", 1, self.model_dump(mode="json"))


class ConstructionCompositionProvenance(HopModel):
    """Exact upstream authorities and implementation identity for composition."""

    hop_version: str
    route_implementation_version: Literal["complete-construction/5"] = "complete-construction/5"
    foldback_result_id: str = Field(pattern=r"^hop:foldback-neighborhood-result/[0-9a-f]{64}@1$")
    basal_result_id: str | None = Field(
        default=None,
        pattern=r"^hop:basal-neighborhood-result/[0-9a-f]{64}@1$",
    )
    source_partition_result_id: str | None = Field(
        default=None,
        pattern=r"^hop:source-partition-result/[0-9a-f]{64}@1$",
        exclude_if=lambda value: value is None,
    )
    source_partition_realization_id: str | None = Field(
        default=None,
        pattern=r"^hop:source-partition-realization/[0-9a-f]{64}@1$",
        exclude_if=lambda value: value is None,
    )
    design_bundle_id: str = Field(min_length=1)
    foldback_realization_ids: tuple[str, ...]
    basal_realization_ids: tuple[str, ...]


class CompositionMaterialAccounting(HopModel):
    """Exact caller material and accepted endpoint sequence totals."""

    source_material_nt: int = Field(ge=0)
    auxiliary_material_nt: int = Field(ge=0)
    endpoint_product_nt: int = Field(ge=0)


class CompositionDispositionStatus(StrEnum):
    """Closed disposition states for one nominal local combination."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TRUNCATED = "truncated"


class CompositionDisposition(HopModel):
    """Exact ordered disposition for one foldback-basal Cartesian pair."""

    ordinal: int = Field(ge=0)
    foldback_realization_id: str = Field(pattern=r"^hop:foldback-realization/[0-9a-f]{64}@1$")
    basal_realization_id: str | None = Field(
        default=None,
        pattern=r"^hop:basal-realization/[0-9a-f]{64}@1$",
    )
    status: CompositionDispositionStatus
    materialized_realization_id: str | None = Field(
        default=None,
        pattern=r"^hop:materialized-construction/[0-9a-f]{64}@1$",
    )
    rejection_reason: CompositionRejectionCode | None = None
    truncation_reason: str | None = None
    candidate_enzyme_programs: int = Field(ge=0)
    recognition_placements_attempted: int = Field(ge=0)
    constraint_systems_attempted: int = Field(ge=0)

    def model_post_init(self, __context: object) -> None:
        accepted = self.materialized_realization_id is not None
        rejected = self.rejection_reason is not None
        truncated = self.truncation_reason is not None
        expected = {
            CompositionDispositionStatus.ACCEPTED: (True, False, False),
            CompositionDispositionStatus.REJECTED: (False, True, False),
            CompositionDispositionStatus.TRUNCATED: (False, False, True),
        }[self.status]
        if (accepted, rejected, truncated) != expected:
            raise ValueError("Combination disposition fields must match its exact status.")


__all__ = [
    "CompositionDisposition",
    "CompositionDispositionStatus",
    "CompositionMaterialAccounting",
    "ConstructionCompositionExecution",
    "ConstructionCompositionProvenance",
]
