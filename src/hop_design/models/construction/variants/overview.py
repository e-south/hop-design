"""Externally fitted preparation coordinates with an explicit molecular comparison."""

from typing import Annotated, Literal, Self

from pydantic import Field, JsonValue, model_validator

from hop_design.models.base import HopModel
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .similarity import InterfaceKey, MolecularDissimilarity, SequenceKey, ShapeKey

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Finite = Annotated[float, Field(allow_inf_nan=False)]
ProcessingKey = Literal["basal_method", "foldback_method", "release_method"]


class OverviewBasis(HopModel):
    shape_scales: dict[ShapeKey, Annotated[int, Field(gt=0)]]
    sequence_keys: tuple[SequenceKey, ...]
    interface_keys: tuple[InterfaceKey, ...]
    processing_keys: tuple[ProcessingKey, ...]
    weights: tuple[Positive, Positive, Positive, Positive]
    # This contract fixes the operations; it does not accept executable expressions.
    distance_policy: dict[str, str] = Field(
        default_factory=lambda: {
            "regional_metric": "normalized_edit",
            "end_word_metric": "hamming",
            "numeric_scaling": "observed_range",
        }
    )

    @property
    def fields(self) -> tuple[str, ...]:
        return tuple(
            f"{block}.{key}"
            for block, keys in (
                ("shape", self.shape_scales),
                ("sequences", self.sequence_keys),
                ("interfaces", self.interface_keys),
                ("processing", self.processing_keys),
            )
            for key in keys
        )

    @model_validator(mode="after")
    def defined_operations(self) -> Self:
        if self.distance_policy != {
            "regional_metric": "normalized_edit",
            "end_word_metric": "hamming",
            "numeric_scaling": "observed_range",
        }:
            raise ValueError(
                "Recorded overviews require normalized edit, Hamming and observed-range comparison."
            )
        if not self.fields or len(set(self.fields)) != len(self.fields):
            raise ValueError("Overview fields must be nonempty and distinct.")
        return self


class OverviewColumn(HopModel):
    key: str = Field(pattern=r"^(shape|sequences|interfaces|processing)\.[a-z_]+$")
    label: str = Field(min_length=1, max_length=80)
    unit: str = Field(max_length=20)
    parameters: tuple[str, ...] = Field(min_length=1)
    active: Literal[True] = True
    dictionary: tuple[JsonValue, ...] = Field(min_length=1)
    indices: tuple[Annotated[int, Field(ge=0)], ...]
    display_dictionary: tuple[str, ...] | None = None

    @model_validator(mode="after")
    def valid_codes(self) -> Self:
        values = [canonical_json_bytes(value) for value in self.dictionary]
        if len(set(values)) != len(values) or any(i >= len(values) for i in self.indices):
            raise ValueError("Overview dictionary codes must resolve to distinct exact values.")
        if self.display_dictionary is not None and len(self.display_dictionary) != len(values):
            raise ValueError("Overview display names must cover its dictionary.")
        return self


class PreparationOverview(HopModel):
    schema_id: Literal["hop.preparation-overview/v1"] = Field(alias="schema")
    snapshot_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    members: tuple[str, ...] = Field(min_length=1)
    coordinates: tuple[tuple[Finite, Finite], ...]
    basis: OverviewBasis
    columns: tuple[OverviewColumn, ...]
    algorithm: Literal["umap"]
    provenance: dict[str, str]

    @model_validator(mode="after")
    def complete_mapping(self) -> Self:
        if len(set(self.members)) != len(self.members) or len(self.coordinates) != len(
            self.members
        ):
            raise ValueError("Every preparation requires one saved coordinate.")
        if tuple(column.key for column in self.columns) != self.basis.fields:
            raise ValueError("Overview columns must follow the complete declared comparison.")
        if any(len(column.indices) != len(self.members) for column in self.columns):
            raise ValueError("Overview columns must cover every preparation.")
        return self

    @property
    def digest(self) -> str:
        return sha256_digest(canonical_json_bytes(self))


class PreparationDissimilarity(MolecularDissimilarity):
    processing: float | None
