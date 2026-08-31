"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source.py

Defines strict file-oriented complete-construction source contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel

from .complete.accounting import CompositionEnumerationPolicy
from .complete.request import (
    LinearSourceMaterializationSpec,
    TypeIisReleaseRequest,
    WholeRouteConstraints,
)
from .payload import ConstructionEndpoint, LocalNeighborhoodFamily, RouteFamily
from .request import LocalNeighborhoodRequest


def _contains_internal_schema_name(value: object) -> bool:
    if isinstance(value, dict):
        return "schema_id" in value or any(
            _contains_internal_schema_name(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_internal_schema_name(item) for item in value)
    return False


class ConstructionCompositionSource(HopModel):
    """Authored endpoint, exact material policy, constraints, and finite bounds."""

    endpoint: ConstructionEndpoint
    materialization: LinearSourceMaterializationSpec
    release: TypeIisReleaseRequest | None = None
    whole_route_constraints: WholeRouteConstraints
    enumeration: CompositionEnumerationPolicy


class ConstructionSource(HopModel):
    """One strict external source for deterministic complete construction."""

    schema_id: Literal["hop.construction-source/v3"] = Field(alias="schema")
    foldback: LocalNeighborhoodRequest
    basal: LocalNeighborhoodRequest | None = None
    composition: ConstructionCompositionSource

    @field_validator("foldback", "basal", mode="before")
    @classmethod
    def parse_local_request(cls, value: object) -> object:
        if value is None or isinstance(value, LocalNeighborhoodRequest):
            return value
        return LocalNeighborhoodRequest.model_validate_json(json.dumps(value))

    @field_validator("composition", mode="before")
    @classmethod
    def parse_composition(cls, value: object) -> object:
        if isinstance(value, ConstructionCompositionSource):
            return value
        return ConstructionCompositionSource.model_validate_json(json.dumps(value))

    @model_validator(mode="before")
    @classmethod
    def reject_internal_schema_name(cls, value: object) -> object:
        if _contains_internal_schema_name(value):
            raise ValueError("Construction source must use the external 'schema' field.")
        return value

    @model_validator(mode="after")
    def validate_route(self) -> ConstructionSource:
        if (
            self.foldback.family is not LocalNeighborhoodFamily.FOLDBACK
            or self.foldback.route_family is not RouteFamily.LINEAR_SOURCE_V1
            or self.foldback.endpoint is not ConstructionEndpoint.SSDNA_HAIRPIN
        ):
            raise ValueError(
                "Construction source foldback must describe the linear-source ssDNA hairpin "
                "intermediate."
            )

        endpoint = self.composition.endpoint
        auxiliaries = (
            self.composition.materialization.adapter,
            self.composition.materialization.forward_primer,
            self.composition.materialization.reverse_primer,
        )
        if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            if self.basal is not None:
                raise ValueError("A direct endpoint must omit basal discovery.")
            if any(item is not None for item in auxiliaries):
                raise ValueError("A direct endpoint must omit adapter and PCR primers.")
            if self.composition.release is not None:
                raise ValueError("A direct endpoint must omit clone release.")
            return self

        if self.basal is None:
            raise ValueError("PCR-bearing endpoints require basal discovery.")
        if any(item is None for item in auxiliaries):
            raise ValueError("PCR-bearing endpoints require an exact adapter and both primers.")
        if (
            self.basal.family is not LocalNeighborhoodFamily.BASAL
            or self.basal.route_family is not RouteFamily.LINEAR_SOURCE_V1
            or self.basal.endpoint is not ConstructionEndpoint.HAIRPIN_PCR_DUPLEX
        ):
            raise ValueError(
                "Basal discovery must resolve the linear source through the hairpin PCR duplex."
            )
        if self.basal.payload.payload_spec_id != self.foldback.payload.payload_spec_id:
            raise ValueError("Foldback and basal discovery must describe the same payload space.")
        if endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            if self.composition.release is not None:
                raise ValueError("A hairpin PCR endpoint must omit clone release.")
        elif self.composition.release is None:
            raise ValueError("A clone-ready endpoint requires exact Type IIS release.")
        return self


__all__ = ["ConstructionCompositionSource", "ConstructionSource"]
