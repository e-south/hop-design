"""Selections constrain a finite observed pool; they never authorize new construction."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from .membership import PreparationQuery
from .parameters import ParameterSelection, validate_selections

type MolecularStage = Literal["hairpin", "endpoint"]
type Neighborhood = Literal["loop", "closing", "assembly", "stem", "interfaces"]
type Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class NeighborhoodPin(HopModel):
    neighborhood: Neighborhood
    variant_ids: tuple[Digest, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def distinct_variants(self) -> NeighborhoodPin:
        if len(self.variant_ids) != len(set(self.variant_ids)):
            raise ValueError("A neighborhood pin must not repeat a variant.")
        return self


class PreservedMolecularProperty(HopModel):
    stage: MolecularStage
    property: Literal[
        "non_loop_sequences", "non_loop_pairing", "terminal_chemistry", "product_identity"
    ]


class PreservedSurroundings(HopModel):
    stage: MolecularStage
    except_neighborhood: Neighborhood


class ScaffoldVariantQuery(PreparationQuery):
    schema_id: Literal["hop.scaffold-variant-query/v1", "hop.scaffold-variant-query/v2"] = Field(
        default="hop.scaffold-variant-query/v1", alias="schema"
    )
    result_digest: Digest
    stage: MolecularStage
    focus: Neighborhood
    reference: str | None = Field(default=None, min_length=1, max_length=200)
    pins: tuple[NeighborhoodPin, ...] = Field(default=(), max_length=5)
    controls: tuple[PreservedMolecularProperty, ...] = Field(default=(), max_length=8)
    surroundings: tuple[PreservedSurroundings, ...] = Field(default=(), max_length=10)
    parameters: tuple[ParameterSelection, ...] = Field(
        default=(), max_length=128, exclude_if=lambda values: not values
    )

    @model_validator(mode="after")
    def explicit_controls(self) -> ScaffoldVariantQuery:
        if (
            self.parameters or self.membership is not None
        ) and self.schema_id != "hop.scaffold-variant-query/v2":
            raise ValueError(
                "Parameter or membership constraints require hop.scaffold-variant-query/v2."
            )
        validate_selections(self.parameters)
        if (self.controls or self.surroundings) and self.reference is None:
            raise ValueError("Preserved properties require an explicit fixed reference.")
        if len({p.neighborhood for p in self.pins}) != len(self.pins):
            raise ValueError("Declare each neighborhood pin once, with its allowed variants.")
        if len({(p.stage, p.property) for p in self.controls}) != len(self.controls):
            raise ValueError("Preserved stage properties must not repeat.")
        if len({(p.stage, p.except_neighborhood) for p in self.surroundings}) != len(
            self.surroundings
        ):
            raise ValueError("Preserved surroundings must not repeat.")
        return self

    def canonical(self) -> ScaffoldVariantQuery:
        return self.model_copy(
            update={
                "parameters": tuple(
                    p.model_copy(update={"values": tuple(sorted(p.values))})
                    if p.values is not None
                    else p
                    for p in sorted(self.parameters, key=lambda p: p.key)
                ),
                "pins": tuple(
                    p.model_copy(update={"variant_ids": tuple(sorted(p.variant_ids))})
                    for p in sorted(self.pins, key=lambda p: p.neighborhood)
                ),
                "controls": tuple(sorted(self.controls, key=lambda c: (c.stage, c.property))),
                "surroundings": tuple(
                    sorted(self.surroundings, key=lambda c: (c.stage, c.except_neighborhood))
                ),
            }
        )
