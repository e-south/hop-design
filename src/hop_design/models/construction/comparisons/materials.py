"""Explicit binding to a previously verified external material specification."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

type MaterialRole = Literal[
    "source_ssdna",
    "source_materialization_forward_primer",
    "source_materialization_reverse_primer",
    "ligation_adapter",
    "endpoint_forward_primer",
    "endpoint_reverse_primer",
]


class SelectedPreparationReference(HopModel):
    bundle_path: str = Field(min_length=1)
    selection_path: str = Field(min_length=1)


class PriorMaterialReuse(HopModel):
    reference: SelectedPreparationReference
    roles: tuple[MaterialRole, ...] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def distinct_roles(self) -> PriorMaterialReuse:
        if len(self.roles) != len(set(self.roles)):
            raise ValueError("Reused prior-material roles must not repeat.")
        return self
