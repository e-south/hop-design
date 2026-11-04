"""Frozen molecular positions; eligibility and display offsets never rewrite geometry."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .neighbors import NeighborGraphReceipt
from .similarity import MolecularComparisonBasis, MolecularDescriptor

Finite = Annotated[float, Field(allow_inf_nan=False)]


class MolecularCoordinate(HopModel):
    comparison_key: str = Field(min_length=1)
    x: Finite
    y: Finite


class SimilarityLayoutSettings(HopModel):
    seed: int = Field(default=17, ge=0, lt=2**32)
    neighbors: int = Field(default=10, ge=2, le=200)
    minimum_distance: float = Field(default=0.1, ge=0, le=1, allow_inf_nan=False)
    epochs: int = Field(default=400, ge=10, le=2000)


class MolecularLandscape(HopModel):
    schema_id: Literal["hop.molecular-landscape/v1", "hop.molecular-landscape/v2"] = Field(
        default="hop.molecular-landscape/v1", alias="schema"
    )
    snapshot_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    basis: MolecularComparisonBasis
    preparations: tuple[MolecularDescriptor, ...] = Field(min_length=1)
    coordinates: tuple[MolecularCoordinate, ...] = Field(min_length=1)
    algorithm: Literal["coincident", "classical_mds", "umap"]
    settings: SimilarityLayoutSettings = Field(default_factory=SimilarityLayoutSettings)
    versions: dict[str, str]
    projector: dict[str, str]
    neighbor_graph: NeighborGraphReceipt | None = Field(
        default=None, exclude_if=lambda v: v is None
    )

    @model_validator(mode="after")
    def complete_mapping(self) -> Self:
        self.basis.effective_policy.validate_end_lengths(self.preparations)
        if (self.schema_id == "hop.molecular-landscape/v2") != (self.neighbor_graph is not None):
            raise ValueError("Sparse neighbor evidence requires molecular-landscape/v2.")
        identities = [p.identity for p in self.preparations]
        signatures = {p.comparison_key for p in self.preparations}
        coordinates = [c.comparison_key for c in self.coordinates]
        if len(set(identities)) != len(identities):
            raise ValueError("A molecular landscape requires distinct preparations.")
        if len(set(coordinates)) != len(coordinates) or set(coordinates) != signatures:
            raise ValueError("Every molecular signature needs exactly one coordinate.")
        if set(self.basis.comparison_keys) != signatures:
            raise ValueError("Comparison basis disagrees with the mapped molecular signatures.")
        if self.neighbor_graph is not None:
            graph = self.neighbor_graph
            if graph.signatures != len(signatures) or graph.seed != self.settings.seed:
                raise ValueError("Neighbor evidence disagrees with the mapped cohort or seed.")
            if not {q.comparison_key for q in graph.audit} <= signatures:
                raise ValueError("Neighbor audit contains a foreign molecular signature.")
            if self.algorithm != "umap":
                raise ValueError("Sparse neighbor coordinates require UMAP.")
        if {p.scope_key for p in self.preparations} != {self.basis.scope_key}:
            raise ValueError("Landscape preparations must share the comparison scope.")
        if any(
            (p.retained_terminal_bases is not None)
            != (self.basis.schema_id == "hop.molecular-comparison/v2")
            for p in self.preparations
        ):
            raise ValueError("Landscape terminal comparison disagrees with the versioned basis.")
        if self.algorithm == "coincident" and (
            len(coordinates) != 1 or self.coordinates[0].x or self.coordinates[0].y
        ):
            raise ValueError("Coincident layout requires one molecular position at the origin.")
        return self

    @property
    def digest(self) -> str:
        return sha256_digest(canonical_json_bytes(self))
