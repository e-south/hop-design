"""Serializable inspection context; molecular selection retains its native contract."""

import json
from math import isfinite
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.surveys.selection import Digest

from .parameters import parameter_definition
from .view_color import AtlasColorLens


class AtlasPresentation(HopModel):
    """Display preferences never enter a molecular identity."""

    landscape: Literal["parameters", "families", "similarity"] = "parameters"
    molecule: Literal["molecule", "route"] = "molecule"
    family_stage: Literal["hairpin", "endpoint"] = "endpoint"
    layout: Literal["auto", "feature_map", "mosaic"] = "auto"
    route: Literal["complete", "assembly"] = "complete"


def _canonical_axes(keys: tuple[str, ...]) -> tuple[str, ...]:
    if len(set(keys)) != len(keys):
        raise ValueError("Display axes must not repeat.")
    for key in keys:
        definition = parameter_definition(key)
        if key != definition.canonical_key:
            raise ValueError(f"Use canonical display axis {definition.canonical_key!r}.")
    return keys


class ProjectedAtlasPresentation(AtlasPresentation):
    """A recorded drawing recipe; omitted axes remain in the molecular data."""

    display_axes: tuple[str, ...] = Field(min_length=1)

    @field_validator("display_axes")
    @classmethod
    def canonical_axes(cls, keys: tuple[str, ...]) -> tuple[str, ...]:
        return _canonical_axes(keys)


class ColoredAtlasPresentation(AtlasPresentation):
    color: AtlasColorLens
    display_axes: tuple[str, ...] | None = Field(
        default=None, min_length=1, exclude_if=lambda value: value is None
    )

    @field_validator("display_axes")
    @classmethod
    def canonical_axes(cls, keys: tuple[str, ...] | None) -> tuple[str, ...] | None:
        return None if keys is None else _canonical_axes(keys)


class AtlasExploration(HopModel):
    """The next seed and visited preparations, not an inferred sampling history."""

    seed: int = Field(default=0, ge=0, lt=2**64)
    strategy: Literal["families", "preparations", "loop"] = "families"
    history: tuple[str, ...] = ()


class _ViewPosition(HopModel):
    pool_digest: Digest
    selection: dict[str, Any]
    stage: str = Field(default="all", min_length=1)
    reference_identity: str | None = None
    camera: tuple[float, float, float, float] | None = None

    @field_validator("camera")
    @classmethod
    def camera_extent(
        cls, value: tuple[float, float, float, float] | None
    ) -> tuple[float, float, float, float] | None:
        if value is not None and (
            not all(isfinite(x) for x in value) or value[2] <= 0 or value[3] <= 0
        ):
            raise ValueError("Camera coordinates must be finite, with positive width and height.")
        return value


class LegacyAtlasViewReceipt(_ViewPosition):
    schema_id: Literal["hop.atlas-view/v1"] = Field(alias="schema")


class _DisplayPosition(_ViewPosition):
    render_policy: Literal["captured", "current"] = "captured"
    presentation: AtlasPresentation = Field(default_factory=AtlasPresentation)
    exploration: AtlasExploration = Field(default_factory=AtlasExploration)


class AtlasViewReceipt(_DisplayPosition):
    schema_id: Literal["hop.atlas-view/v2"] = Field(default="hop.atlas-view/v2", alias="schema")

    @model_validator(mode="after")
    def existing_landscape(self) -> "AtlasViewReceipt":
        if self.presentation.landscape == "similarity":
            raise ValueError("Similarity views require v3 with their coordinate digest.")
        return self


class MolecularAtlasViewReceipt(_DisplayPosition):
    schema_id: Literal["hop.atlas-view/v3"] = Field(default="hop.atlas-view/v3", alias="schema")
    landscape_digest: Digest

    @model_validator(mode="after")
    def molecular_landscape(self) -> "MolecularAtlasViewReceipt":
        if self.presentation.landscape != "similarity":
            raise ValueError("A coordinate-bound view must use the molecular similarity map.")
        return self


class _CoordinatePosition(_DisplayPosition):
    landscape_digest: Digest | None = None

    @model_validator(mode="after")
    def coordinate_binding(self) -> "_CoordinatePosition":
        if (self.presentation.landscape == "similarity") != (self.landscape_digest is not None):
            raise ValueError("Only similarity views require the saved coordinate digest.")
        return self


class ProjectedAtlasViewReceipt(_CoordinatePosition):
    schema_id: Literal["hop.atlas-view/v4"] = Field(default="hop.atlas-view/v4", alias="schema")
    presentation: ProjectedAtlasPresentation


class ColoredAtlasViewReceipt(_CoordinatePosition):
    schema_id: Literal["hop.atlas-view/v5"] = Field(default="hop.atlas-view/v5", alias="schema")
    presentation: ColoredAtlasPresentation


ViewReceipt = (
    AtlasViewReceipt
    | MolecularAtlasViewReceipt
    | ProjectedAtlasViewReceipt
    | ColoredAtlasViewReceipt
)


def parse_view_receipt(
    raw: dict[str, Any],
) -> ViewReceipt:
    """Validate v1 before migrating; unknown fields and schemas never disappear."""
    if raw.get("schema") == "hop.atlas-view/v1":
        old = LegacyAtlasViewReceipt.model_validate_json(json.dumps(raw))
        raw = {**old.model_dump(mode="json", by_alias=True), "schema": "hop.atlas-view/v2"}
    if raw.get("schema") == "hop.atlas-view/v3":
        return MolecularAtlasViewReceipt.model_validate_json(json.dumps(raw))
    if raw.get("schema") == "hop.atlas-view/v4":
        return ProjectedAtlasViewReceipt.model_validate_json(json.dumps(raw))
    if raw.get("schema") == "hop.atlas-view/v5":
        return ColoredAtlasViewReceipt.model_validate_json(json.dumps(raw))
    return AtlasViewReceipt.model_validate_json(json.dumps(raw))
