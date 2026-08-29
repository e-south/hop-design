"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/realization.py

Defines payload-centered construction contracts and discovery evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import (
    normalize_dna_sequence,
)

from .payload import ConstructionEndpoint, _content_id
from .relaxation import EnumerationPolicy
from .targets import LocalGeometryTarget


class ConstructionExecution(HopModel):
    """Replay identity for one bounded execution of a scientific construction problem."""

    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    hop_version: str
    route_implementation_version: str
    enumeration: EnumerationPolicy
    max_operations: int | None = Field(ge=1)
    environment: dict[str, str]

    @property
    def execution_id(self) -> str:
        """Return identity including implementation and replay-relevant execution facts."""
        return _content_id("execution", 1, self.model_dump(mode="json"))


class LocalRealization(HopModel):
    """One exact local sequence, enzyme binding, stage program, and achieved geometry."""

    local_realization_id: str = Field(pattern=r"^hop:local-realization/[0-9a-f]{64}@1$")
    local_sequence: str
    enzyme_binding_ids: tuple[str, ...]
    stage_ids: tuple[str, ...]
    achieved_geometry: LocalGeometryTarget

    @field_validator("local_sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Local realization sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @classmethod
    def create(
        cls,
        *,
        local_sequence: str,
        enzyme_binding_ids: tuple[str, ...],
        stage_ids: tuple[str, ...],
        achieved_geometry: LocalGeometryTarget,
    ) -> LocalRealization:
        """Create a content-addressed exact local realization."""
        content = {
            "local_sequence": normalize_dna_sequence(local_sequence, allow_degenerate=False),
            "enzyme_binding_ids": enzyme_binding_ids,
            "stage_ids": stage_ids,
            "achieved_geometry": achieved_geometry.model_dump(mode="json"),
        }
        return cls(
            local_realization_id=_content_id("local-realization", 1, content),
            local_sequence=local_sequence,
            enzyme_binding_ids=enzyme_binding_ids,
            stage_ids=stage_ids,
            achieved_geometry=achieved_geometry,
        )

    @model_validator(mode="after")
    def validate_identity(self) -> LocalRealization:
        expected = _content_id(
            "local-realization",
            1,
            {
                "local_sequence": self.local_sequence,
                "enzyme_binding_ids": self.enzyme_binding_ids,
                "stage_ids": self.stage_ids,
                "achieved_geometry": self.achieved_geometry.model_dump(mode="json"),
            },
        )
        if self.local_realization_id != expected:
            raise ValueError("local_realization_id must match the complete local realization.")
        return self


class FinalProductReference(HopModel):
    """Exact endpoint sequence, end descriptors, and topology."""

    final_product_id: str = Field(pattern=r"^hop:final-product/[0-9a-f]{64}@1$")
    endpoint: ConstructionEndpoint
    sequence: str
    topology: str
    end_descriptors: tuple[str, ...]

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Final product sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @classmethod
    def create(
        cls,
        *,
        endpoint: ConstructionEndpoint,
        sequence: str,
        topology: str,
        end_descriptors: tuple[str, ...],
    ) -> FinalProductReference:
        """Create a content-addressed exact final product reference."""
        content = {
            "endpoint": endpoint,
            "sequence": normalize_dna_sequence(sequence, allow_degenerate=False),
            "topology": topology,
            "end_descriptors": end_descriptors,
        }
        return cls(
            final_product_id=_content_id("final-product", 1, content),
            endpoint=endpoint,
            sequence=sequence,
            topology=topology,
            end_descriptors=end_descriptors,
        )

    @model_validator(mode="after")
    def validate_identity(self) -> FinalProductReference:
        expected = _content_id(
            "final-product",
            1,
            {
                "endpoint": self.endpoint,
                "sequence": self.sequence,
                "topology": self.topology,
                "end_descriptors": self.end_descriptors,
            },
        )
        if self.final_product_id != expected:
            raise ValueError("final_product_id must match the exact endpoint product.")
        return self


class CompleteConstructionRealization(HopModel):
    """One complete precursor, route trajectory, and exact endpoint product relation."""

    complete_realization_id: str = Field(pattern=r"^hop:complete-realization/[0-9a-f]{64}@1$")
    precursor_sequence: str
    local_realization_ids: tuple[str, ...] = Field(min_length=1)
    stage_ids: tuple[str, ...] = Field(min_length=1)
    final_product_id: str = Field(pattern=r"^hop:final-product/[0-9a-f]{64}@1$")

    @field_validator("precursor_sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Construction precursor must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @classmethod
    def create(
        cls,
        *,
        precursor_sequence: str,
        local_realization_ids: tuple[str, ...],
        stage_ids: tuple[str, ...],
        final_product_id: str,
    ) -> CompleteConstructionRealization:
        """Create a content-addressed complete route realization."""
        content = {
            "precursor_sequence": normalize_dna_sequence(
                precursor_sequence, allow_degenerate=False
            ),
            "local_realization_ids": local_realization_ids,
            "stage_ids": stage_ids,
            "final_product_id": final_product_id,
        }
        return cls(
            complete_realization_id=_content_id("complete-realization", 1, content),
            precursor_sequence=precursor_sequence,
            local_realization_ids=local_realization_ids,
            stage_ids=stage_ids,
            final_product_id=final_product_id,
        )

    @model_validator(mode="after")
    def validate_identity(self) -> CompleteConstructionRealization:
        expected = _content_id(
            "complete-realization",
            1,
            {
                "precursor_sequence": self.precursor_sequence,
                "local_realization_ids": self.local_realization_ids,
                "stage_ids": self.stage_ids,
                "final_product_id": self.final_product_id,
            },
        )
        if self.complete_realization_id != expected:
            raise ValueError("complete_realization_id must match the complete route relation.")
        return self
