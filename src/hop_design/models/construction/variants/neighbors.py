"""Numerical neighbor search policy and its measured, edition-local quality."""

from typing import Any, Literal, Self

from pydantic import Field, field_serializer, field_validator, model_validator

from hop_design.models.base import HopModel

from .query import Digest


class NeighborSearchSettings(HopModel):
    strategy: Literal["landmark_candidates", "molecular_neighbor_descent"] = (
        "molecular_neighbor_descent"
    )
    landmarks: int = Field(default=32, ge=4, le=128)
    candidates: int = Field(default=64, ge=16, le=4096)
    max_candidates: int = Field(default=2048, ge=16, le=4096)
    audit_queries: int = Field(default=128, ge=1, le=1024)
    required_recall: float = Field(default=0.95, ge=0.95, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered_limits(self) -> Self:
        if self.max_candidates < self.candidates:
            raise ValueError("Maximum candidates must cover the initial candidate count.")
        return self


class NeighborAuditQuery(HopModel):
    comparison_key: Digest
    structural_class: Digest
    recall: float = Field(ge=0, le=1, allow_inf_nan=False)


class NeighborGraphReceipt(HopModel):
    schema_id: Literal["hop.molecular-neighbor-graph/v1"] = Field(
        default="hop.molecular-neighbor-graph/v1", alias="schema"
    )
    strategy: Literal[
        "landmark_candidates_exact_rerank", "molecular_neighbor_descent_exact_rerank"
    ] = "landmark_candidates_exact_rerank"
    settings: NeighborSearchSettings
    seed: int = Field(ge=0, lt=2**32)
    signatures: int = Field(ge=2)
    retained_neighbors: int = Field(ge=2)
    candidates_examined_per_query: int = Field(ge=1)
    distance_evaluations: int = Field(ge=1)
    audit_k: int = Field(ge=1, le=15)
    audited_queries: int = Field(ge=1)
    structural_classes: int = Field(ge=1)
    minimum_recall: float = Field(ge=0, le=1, allow_inf_nan=False)
    audit: tuple[NeighborAuditQuery, ...] = Field(min_length=1)
    graph_digest: Digest

    @field_validator("settings", mode="before")
    @classmethod
    def captured_policy(cls, value: Any) -> Any:
        # Historical graph receipts omitted the then-default strategy. Confine
        # that interpretation to captured evidence, never new runtime policies.
        if isinstance(value, dict) and "strategy" not in value:
            return {"strategy": "landmark_candidates", "candidates": 128, **value}
        return value

    @field_serializer("settings")
    def captured_settings(self, settings: NeighborSearchSettings) -> dict[str, Any]:
        result = settings.model_dump(mode="json")
        if settings.strategy == "landmark_candidates":
            result.pop("strategy")
        return result

    @model_validator(mode="after")
    def checked_quality(self) -> Self:
        if self.strategy != f"{self.settings.strategy}_exact_rerank":
            raise ValueError("Neighbor strategy disagrees with its saved settings.")
        if len(self.audit) != self.audited_queries or len(
            {q.comparison_key for q in self.audit}
        ) != len(self.audit):
            raise ValueError("Neighbor audit must identify each examined query exactly once.")
        if self.minimum_recall != min(q.recall for q in self.audit):
            raise ValueError("Neighbor minimum recall disagrees with the audit.")
        if self.minimum_recall < self.settings.required_recall:
            raise ValueError("Neighbor recall does not meet the declared threshold.")
        if self.retained_neighbors > self.signatures or self.audited_queries > self.signatures:
            raise ValueError("Neighbor counts exceed the comparison cohort.")
        return self
