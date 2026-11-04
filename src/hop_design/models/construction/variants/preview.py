"""Browsing an observed variant never edits permissions or selects a preparation."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from .inspection import MolecularAddress
from .query import Digest


class MolecularViewReference(HopModel):
    option_label: str = Field(min_length=1, max_length=200)
    state: str = Field(min_length=1, max_length=200)


class ScaffoldVariantPreviewRequest(HopModel):
    schema_id: Literal["hop.scaffold-variant-preview-request/v1"] = Field(
        default="hop.scaffold-variant-preview-request/v1", alias="schema"
    )
    result_digest: Digest
    query_digest: Digest
    variant_id: Digest
    state: str = Field(default="hairpin", min_length=1, max_length=200)
    option_label: str | None = Field(default=None, min_length=1, max_length=200)
    focus: MolecularAddress | None = None
    focus_option_label: str | None = Field(default=None, min_length=1, max_length=200)
    focus_mode: Literal["material", "comparison"] = "material"
    view_from: MolecularViewReference | None = None

    @model_validator(mode="after")
    def bound_focus(self) -> "ScaffoldVariantPreviewRequest":
        if (self.focus is None) != (self.focus_option_label is None):
            raise ValueError("An inspected position must name its originating preparation.")
        return self
