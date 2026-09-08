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
from .search import BasalGeometryDomain, LocalGeometryDomain, NeighborhoodSearchPlan
from .targets import (
    BasalPairAllowance,
    ConstructionConstraints,
    ConstructionPreferences,
    LocalGeometryTarget,
)


class LocalNeighborhoodRequest(HopModel):
    """Shared payload-centered request envelope for foldback or basal discovery."""

    schema_id: Literal["hop.local-neighborhood-request/v6"] = Field(
        default="hop.local-neighborhood-request/v6", alias="schema"
    )
    name: str | None = None
    payload: FinalPayloadReference
    family: LocalNeighborhoodFamily
    route_family: RouteFamily
    endpoint: ConstructionEndpoint
    geometry_domain: LocalGeometryDomain
    hard_constraints: ConstructionConstraints
    preferences: ConstructionPreferences = ConstructionPreferences()
    enzyme_provisioning: EnzymeProvisioningPolicy
    search: NeighborhoodSearchPlan

    @model_validator(mode="after")
    def validate_request(self) -> LocalNeighborhoodRequest:
        if self.geometry_domain.family != self.family.value:
            raise ValueError("Local neighborhood family must match the geometry domain.")
        if self.route_family is RouteFamily.LINEAR_SOURCE_V1:
            validate_linear_source_payload(self.payload)
        if (
            self.search.sequence_partition is not None
            and self.hard_constraints.require_all_members_compatible
        ):
            raise ValueError(
                "Sequence-domain partitioning cannot establish all-member compatibility."
            )
        if isinstance(self.geometry_domain, BasalGeometryDomain):
            self._validate_basal_endpoint(self.geometry_domain)
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

    def _validate_basal_endpoint(self, domain: BasalGeometryDomain) -> None:
        if self.endpoint not in {
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            ConstructionEndpoint.CLONE_READY_DUPLEX,
        }:
            raise ValueError("Basal local discovery requires a PCR-bearing construction endpoint.")
        if self.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX and (
            domain.future_release is not None
        ):
            raise ValueError("A hairpin PCR basal search must omit future end generation.")
        if self.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX and (
            domain.future_release is None
        ):
            raise ValueError("A clone-ready basal search requires future end generation.")
        if domain.pairing_constraints[0].allowed_class is not BasalPairAllowance.MATCH:
            raise ValueError("A PCR-bearing basal search requires a payload-proximal match.")


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
            "geometry_domain": request.geometry_domain.model_dump(mode="json"),
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
            "search": {
                "max_retained_overhead_nt": request.search.max_retained_overhead_nt,
                "scope": request.search.scope,
            },
        },
    )
