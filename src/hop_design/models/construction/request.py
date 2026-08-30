"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/request.py

Defines payload-centered construction contracts and discovery evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import (
    EnzymeProvisioningPolicy,
    characterized_enzyme_catalog_digest,
)

from .payload import (
    ConstructionEndpoint,
    FinalPayloadReference,
    LocalNeighborhoodFamily,
    RouteFamily,
    _content_id,
    validate_linear_source_payload,
)
from .relaxation import EnumerationPolicy, RelaxationPolicy, geometry_coordinate_value
from .targets import (
    BasalTarget,
    ConstructionConstraints,
    ConstructionPreferences,
    LocalGeometryTarget,
)


class LocalNeighborhoodRequest(HopModel):
    """Shared payload-centered request envelope for foldback or basal discovery."""

    schema_id: Literal["hop.local-neighborhood-request/v2"] = Field(
        default="hop.local-neighborhood-request/v2", alias="schema"
    )
    name: str | None = None
    payload: FinalPayloadReference
    family: LocalNeighborhoodFamily
    route_family: RouteFamily
    endpoint: ConstructionEndpoint
    target: LocalGeometryTarget
    hard_constraints: ConstructionConstraints
    preferences: ConstructionPreferences = ConstructionPreferences()
    enzyme_provisioning: EnzymeProvisioningPolicy
    relaxation: RelaxationPolicy
    enumeration: EnumerationPolicy

    @model_validator(mode="after")
    def validate_request(self) -> LocalNeighborhoodRequest:
        if self.target.family != self.family.value:
            raise ValueError("Local neighborhood family must match the target family.")
        if self.route_family is RouteFamily.LINEAR_SOURCE_V1:
            validate_linear_source_payload(self.payload)
        for coordinate in self.relaxation.coordinates:
            try:
                exact_value = geometry_coordinate_value(self.target, coordinate.name)
            except ValueError as error:
                raise ValueError(
                    "Relaxation coordinates must name integer target fields: " + coordinate.name
                ) from error
            if not coordinate.minimum <= exact_value <= coordinate.maximum:
                raise ValueError(
                    f"The exact target for {coordinate.name} lies outside its relaxation bounds."
                )
        if isinstance(self.target, BasalTarget):
            self._validate_basal_endpoint(self.target)
        catalog_ids = {enzyme.enzyme_id for enzyme in self.enzyme_provisioning.catalog.enzymes}
        unknown_preferred = set(self.preferences.preferred_enzyme_ids) - catalog_ids
        if unknown_preferred:
            raise ValueError(
                "Construction preferences reference unknown enzymes: "
                + ", ".join(sorted(unknown_preferred))
            )
        return self

    @property
    def enzyme_catalog_id(self) -> str:
        """Return the embedded characterized-catalog identifier."""
        return self.enzyme_provisioning.catalog.catalog_id

    @property
    def enzyme_catalog_digest(self) -> str:
        """Return molecular catalog identity independent of procurement metadata."""
        return characterized_enzyme_catalog_digest(self.enzyme_provisioning.catalog)

    def _validate_basal_endpoint(self, target: BasalTarget) -> None:
        if self.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            if target.end_generation is not None:
                raise ValueError("ssdna_hairpin must not request end generation.")
            if target.pairing_constraints or target.ligation_proximal_match_required:
                raise ValueError("ssdna_hairpin must not invent adapter-pairing requirements.")
            return
        if not target.pairing_constraints:
            raise ValueError(f"{self.endpoint.value} requires pairing constraints.")
        if not target.ligation_proximal_match_required:
            raise ValueError(f"{self.endpoint.value} requires a payload-proximal match.")
        if self.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            if target.end_generation is not None:
                raise ValueError("hairpin_pcr_duplex must not request clone-ready end generation.")
        elif target.end_generation is None:
            raise ValueError("clone_ready_duplex requires an end-generation request.")


def geometry_id(target: LocalGeometryTarget) -> str:
    """Return identity for only the canonical family-specific geometry fields."""
    return _content_id("geometry", 1, target.model_dump(mode="json"))


def problem_id(request: LocalNeighborhoodRequest) -> str:
    """Return scientific problem identity without labels or resource limits."""
    return _content_id(
        "construction-problem",
        1,
        {
            "schema": request.schema_id,
            "payload_spec_id": request.payload.payload_spec_id,
            "family": request.family,
            "route_family": request.route_family,
            "endpoint": request.endpoint,
            "target": request.target.model_dump(mode="json"),
            "hard_constraints": request.hard_constraints.model_dump(mode="json"),
            "enzyme_catalog_id": request.enzyme_catalog_id,
            "enzyme_catalog_digest": request.enzyme_catalog_digest,
            "enzyme_provisioning": {
                "allowed_enzyme_ids": sorted(request.enzyme_provisioning.allowed_enzyme_ids),
                "forbidden_enzyme_ids": sorted(request.enzyme_provisioning.forbidden_enzyme_ids),
                "reserved_enzyme_ids": sorted(request.enzyme_provisioning.reserved_enzyme_ids),
                "role_restrictions": sorted(
                    (
                        {
                            "role": restriction.role,
                            "allowed_enzyme_ids": sorted(restriction.allowed_enzyme_ids),
                        }
                        for restriction in request.enzyme_provisioning.role_restrictions
                    ),
                    key=lambda item: str(item["role"]),
                ),
            },
            "relaxation": {
                **request.relaxation.model_dump(mode="json", exclude={"coordinates"}),
                "coordinates": sorted(
                    (
                        coordinate.model_dump(mode="json")
                        for coordinate in request.relaxation.coordinates
                    ),
                    key=lambda item: item["name"],
                ),
            },
        },
    )
