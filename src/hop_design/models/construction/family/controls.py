"""A requirement and an observed agreement carry different claims."""

from typing import Literal

from hop_design.models.base import HopModel

from .request import SharedProperty


class ComparisonControl(HopModel):
    property: SharedProperty
    required: bool
    reference: str | None
    members: tuple[str, ...]
    status: Literal["required_and_verified", "observed_agreement", "different", "not_assessed"]
    differing_members: tuple[str, ...]
    unassessed_members: tuple[str, ...]
