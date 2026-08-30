"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/relaxation.py

Defines payload-centered construction contracts and discovery evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import cast

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel

from .targets import LocalGeometryTarget


class RelaxationMode(StrEnum):
    """Declared stopping semantics for discrete geometry relaxation."""

    EXACT_ONLY = "exact_only"
    FIRST_FEASIBLE_SHELL = "first_feasible_shell"
    THROUGH_RADIUS = "through_radius"


class RelaxationCoordinate(HopModel):
    """One explicitly enabled integer target coordinate and its hard bounds."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
    minimum: int
    maximum: int

    @model_validator(mode="after")
    def validate_bounds(self) -> RelaxationCoordinate:
        if self.maximum < self.minimum:
            raise ValueError("Relaxation-coordinate maximum must not precede its minimum.")
        return self


class RelaxationPolicy(HopModel):
    """Exact-first discrete relaxation with explicit enabled coordinates."""

    mode: RelaxationMode
    max_radius: int = Field(ge=0)
    coordinates: tuple[RelaxationCoordinate, ...] = ()

    @field_validator("coordinates", mode="after")
    @classmethod
    def canonicalize_coordinates(
        cls, values: tuple[RelaxationCoordinate, ...]
    ) -> tuple[RelaxationCoordinate, ...]:
        return tuple(sorted(values, key=lambda item: item.name))

    @model_validator(mode="after")
    def validate_policy(self) -> RelaxationPolicy:
        names = tuple(coordinate.name for coordinate in self.coordinates)
        if len(names) != len(set(names)):
            raise ValueError("Relaxation-coordinate names must be unique.")
        if self.mode is RelaxationMode.EXACT_ONLY and self.max_radius != 0:
            raise ValueError("exact_only relaxation requires max_radius=0.")
        if self.max_radius > 0 and not self.coordinates:
            raise ValueError("A positive relaxation radius requires enabled coordinates.")
        return self


class SequenceDomainPartition(HopModel):
    """One disjoint part of canonical exact sequence-solution enumeration."""

    part_count: int = Field(ge=2, le=256)
    part_index: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_index(self) -> SequenceDomainPartition:
        if self.part_index >= self.part_count:
            raise ValueError("sequence-partition part_index must be less than part_count.")
        return self


class EnumerationPolicy(HopModel):
    """Finite execution limits that do not change the scientific problem identity."""

    max_search_nodes: int = Field(ge=1)
    max_realizations: int = Field(ge=1)
    sequence_partition: SequenceDomainPartition | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )


def geometry_coordinate_value(target: LocalGeometryTarget, coordinate_name: str) -> int:
    """Resolve one integer geometry coordinate, including declared nested fields."""
    current: object = target
    for field_name in coordinate_name.split("."):
        if not isinstance(current, HopModel) or field_name not in type(current).model_fields:
            raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
        current = getattr(current, field_name)
    if not isinstance(current, int) or isinstance(current, bool):
        raise ValueError(f"Relaxation coordinate {coordinate_name} must be an integer.")
    return current


def geometry_with_coordinate_value(
    target: LocalGeometryTarget,
    coordinate_name: str,
    value: int,
) -> LocalGeometryTarget:
    """Return one target copy with a declared integer coordinate replaced."""

    def replace(model: HopModel, path: tuple[str, ...]) -> HopModel:
        field_name, *remaining = path
        if field_name not in type(model).model_fields:
            raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
        if not remaining:
            return model.model_copy(update={field_name: value})
        child = getattr(model, field_name)
        if not isinstance(child, HopModel):
            raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
        return model.model_copy(update={field_name: replace(child, tuple(remaining))})

    return cast(LocalGeometryTarget, replace(target, tuple(coordinate_name.split("."))))


def geometry_fixed_projection(
    target: LocalGeometryTarget,
    relaxed_coordinate_names: set[str],
) -> dict[str, object]:
    """Return geometry content with explicitly relaxed leaves removed."""
    projection = target.model_dump(mode="json")
    for coordinate_name in relaxed_coordinate_names:
        cursor: object = projection
        parts = coordinate_name.split(".")
        for field_name in parts[:-1]:
            if not isinstance(cursor, dict) or field_name not in cursor:
                raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
            cursor = cursor[field_name]
        if not isinstance(cursor, dict) or parts[-1] not in cursor:
            raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
        del cursor[parts[-1]]
    return projection
