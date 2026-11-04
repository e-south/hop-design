"""Read-only molecular answers, separate from requests and exact selections."""

from typing import Any, Literal

from pydantic import Field

from hop_design.models.base import HopModel

from ..variants.parameter_contract import ParameterDefinition

DesignStatus = Literal["choices_available", "no_recorded_match", "excluded_within_scope"]
DesignAction = Literal[
    "select", "inspect_permissions", "refine_query", "continue_search", "revise_request"
]


class DesignParameter(ParameterDefinition):
    applicable: bool
    reason: str | None
    declared_domain: dict[str, Any]
    observed_values: tuple[int | str, ...]


class AvailableDesign(HopModel):
    materialized_realization_id: str
    values: dict[str, int | str | None]
    methods: tuple[str, ...] = ()


class DesignExplanation(HopModel):
    schema_id: Literal["hop.design-explanation/v1"] = Field(
        default="hop.design-explanation/v1", alias="schema"
    )
    product: Literal["hairpin", "adapter_ligated_hairpin", "released_insert", "hairpin_pcr_duplex"]
    context_id: str
    status: DesignStatus
    headline: str
    guidance: str
    matching_preparations: int = Field(ge=0)
    matching_products: dict[str, int]
    choices: tuple[AvailableDesign, ...]
    actions: tuple[DesignAction, ...]
    coverage: dict[str, Any]
    parameters: tuple[DesignParameter, ...] = ()
