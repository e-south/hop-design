"""Hard requirements on the joined hairpin, distinct from search and preference."""

from __future__ import annotations

import json
from typing import Literal, get_args

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from .search import FoldbackGeometryDomain

type ScaffoldDimension = Literal[
    "open_side_paired_positions",
    "loop_side_paired_bp",
    "loop_nt",
    "five_prime_unpaired_nt",
    "three_prime_unpaired_nt",
]
SCAFFOLD_DIMENSIONS = get_args(ScaffoldDimension.__value__)


class ScaffoldCountRange(HopModel):
    """Inclusive finite integer interval; equal boundaries express an exact value."""

    minimum: int = Field(ge=0)
    maximum: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> ScaffoldCountRange:
        if self.minimum > self.maximum:
            raise ValueError("A scaffold range minimum must not exceed its maximum.")
        return self

    def contains(self, value: int) -> bool:
        return self.minimum <= value <= self.maximum


class HairpinScaffoldRequirements(HopModel):
    """Achieved-state requirements; these never expand or relax the searched domain."""

    open_side_paired_positions: ScaffoldCountRange | None = None
    loop_side_paired_bp: ScaffoldCountRange | None = None
    loop_nt: ScaffoldCountRange | None = None
    five_prime_unpaired_nt: ScaffoldCountRange | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    three_prime_unpaired_nt: ScaffoldCountRange | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def require_dimension(self) -> HairpinScaffoldRequirements:
        if all(getattr(self, dimension) is None for dimension in SCAFFOLD_DIMENSIONS):
            raise ValueError("Hairpin scaffold requirements must specify at least one dimension.")
        return self


class ScaffoldMismatch(HopModel):
    """One exact achieved dimension outside a required inclusive interval."""

    dimension: ScaffoldDimension
    required: ScaffoldCountRange
    observed: int = Field(ge=0)
    state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")

    @model_validator(mode="after")
    def validate_mismatch(self) -> ScaffoldMismatch:
        if self.required.contains(self.observed):
            raise ValueError("A scaffold mismatch must be outside its required range.")
        return self


def constrain_foldback_geometry(
    domain: FoldbackGeometryDomain,
    *,
    maximum: int,
    requirements: HairpinScaffoldRequirements | None,
) -> FoldbackGeometryDomain:
    """Apply the same hard dimension intersection before single or survey discovery."""
    if requirements is None:
        return domain
    geometry = domain.model_dump(mode="json")
    for key, floor, required in (
        ("loop_lengths_nt", domain.minimum_loop_length_nt, requirements.loop_nt),
        (
            "annealing_arm_lengths_bp",
            domain.minimum_annealing_arm_length_bp,
            requirements.loop_side_paired_bp,
        ),
    ):
        if required is None:
            continue
        values = geometry[key]
        if not values:
            lower = max(floor, required.minimum)
            upper = min(maximum, required.maximum)
            if upper - lower + 1 > 100_000:
                raise ValueError(
                    "Scaffold expansion exceeds 100000 geometry values; narrow the range."
                )
            values = range(lower, upper + 1)
        selected = [value for value in values if required.contains(value)]
        if not selected:
            dimension = "loop_nt" if key == "loop_lengths_nt" else "loop_side_paired_bp"
            permitted = str(list(values)) if len(values) <= 20 else f"{min(values)}..{max(values)}"
            raise ValueError(
                f"Hairpin scaffold requirement does not intersect {key}: "
                f"requested scaffold.{dimension} {required.minimum}..{required.maximum}; "
                f"permitted values {permitted}. Edit scaffold.{dimension} or the "
                f"context's foldback.geometry.{key} explicitly."
            )
        geometry[key] = selected
    if domain.loop_sequences is not None:
        lengths = geometry["loop_lengths_nt"]
        words = [word for word in domain.loop_sequences if not lengths or len(word) in lengths]
        if not words:
            raise ValueError("Hairpin scaffold requirement does not intersect loop_sequences.")
        geometry["loop_sequences"] = words
    return FoldbackGeometryDomain.model_validate_json(json.dumps(geometry))


__all__ = ["HairpinScaffoldRequirements", "ScaffoldCountRange", "ScaffoldMismatch"]
