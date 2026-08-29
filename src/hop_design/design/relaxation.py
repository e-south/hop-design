"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/relaxation.py

Enumerates deterministic exact-first Manhattan shells for local target geometry.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from itertools import product

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.construction import (
    LocalGeometryTarget,
    RelaxationMode,
    RelaxationPolicy,
)


class RelaxationShell(HopModel):
    """All valid integer target geometries at one declared Manhattan radius."""

    radius: int = Field(ge=0)
    geometries: tuple[LocalGeometryTarget, ...] = Field(min_length=1)


def relaxation_shells(
    target: LocalGeometryTarget,
    policy: RelaxationPolicy,
) -> tuple[RelaxationShell, ...]:
    """Enumerate exact geometry first, then complete direction-neutral shells."""
    if policy.mode is RelaxationMode.EXACT_ONLY:
        return (RelaxationShell(radius=0, geometries=(target,)),)

    target_fields = type(target).model_fields
    coordinates = tuple(sorted(policy.coordinates, key=lambda item: item.name))
    for coordinate in coordinates:
        if coordinate.name not in target_fields:
            raise ValueError(f"Unknown relaxation coordinate: {coordinate.name}.")
        target_value = getattr(target, coordinate.name)
        if not isinstance(target_value, int) or isinstance(target_value, bool):
            raise ValueError(f"Relaxation coordinate {coordinate.name} must be an integer.")
        if not coordinate.minimum <= target_value <= coordinate.maximum:
            raise ValueError(
                f"Exact target for {coordinate.name} must lie within its relaxation bounds."
            )

    target_values = tuple(getattr(target, coordinate.name) for coordinate in coordinates)
    coordinate_domains = tuple(
        range(coordinate.minimum, coordinate.maximum + 1) for coordinate in coordinates
    )
    shells: list[RelaxationShell] = [RelaxationShell(radius=0, geometries=(target,))]
    for radius in range(1, policy.max_radius + 1):
        geometry_values = tuple(
            values
            for values in product(*coordinate_domains)
            if sum(
                abs(value - requested)
                for value, requested in zip(values, target_values, strict=True)
            )
            == radius
        )
        if not geometry_values:
            continue
        geometries = tuple(
            target.model_copy(
                update={
                    coordinate.name: value
                    for coordinate, value in zip(coordinates, values, strict=True)
                }
            )
            for values in geometry_values
        )
        shells.append(RelaxationShell(radius=radius, geometries=geometries))
    return tuple(shells)


__all__ = ["RelaxationShell", "relaxation_shells"]
