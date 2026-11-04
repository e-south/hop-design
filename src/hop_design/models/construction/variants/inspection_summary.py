"""Small navigation facts; exact molecules remain in the referenced atlas record."""

from typing import Any, Literal

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.construction.variants.inspection import MolecularAddress

from ..projections.inspection import InspectionStateChoice
from ..projections.overhead.complete import ConstructionCost


class InspectionStateSummary(HopModel):
    state: InspectionStateChoice


class InspectionAtlasSummary(HopModel):
    materialized_realization_id: str
    states: tuple[InspectionStateSummary, ...]
    construction_cost: ConstructionCost | None


class InspectionLinkSummary(HopModel):
    reference: MolecularAddress
    target: MolecularAddress


class InspectionTransitionSummary(HopModel):
    links: tuple[InspectionLinkSummary, ...]


class InspectionComparisonSummary(HopModel):
    reference: str
    description: str | None
    transitions: tuple[InspectionTransitionSummary, ...]
    notices: tuple[str, ...]
    reference_loop: str
    observed_loop: str
    material_roles: tuple[str, ...]


class RoutePresentationSummary(HopModel):
    requested: Literal["complete", "assembly"]
    effective: Literal["complete", "assembly"]
    displayed_states: int = Field(ge=0)
    recorded_states: int = Field(ge=1)


class InspectionRendering(HopModel):
    requested: Literal["captured", "current"]
    effective: Literal["captured", "current"]
    renderer: dict[str, str] | None
    notice: str | None
    route: RoutePresentationSummary | None = None


class InspectionSummary(HopModel):
    schema_id: Literal["hop.inspection-summary/v1"] = Field(
        default="hop.inspection-summary/v1", alias="schema"
    )
    selection: dict[str, Any]
    atlas: InspectionAtlasSummary
    comparison: InspectionComparisonSummary | None
    rendering: InspectionRendering | None
