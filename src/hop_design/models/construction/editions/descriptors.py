"""Captured comparison rows admitted together, before any molecular inspection."""

from typing import Literal

from pydantic import ConfigDict, Field

from hop_design.models.base import HopModel
from hop_design.models.construction.variants.similarity import MolecularDescriptor


class CapturedDescriptorIndex(HopModel):
    # This saved envelope has one spelling; Python field names are not wire aliases.
    model_config = ConfigDict(validate_by_name=False)

    schema_id: Literal["hop.molecular-descriptor-index/v1"] = Field(alias="schema")
    snapshot_digest: str
    preparations: tuple[MolecularDescriptor, ...]
