"""Author one product intent and expand only into existing molecular contracts."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import (
    CharacterizedEnzymeCatalog,
    EnzymePermissions,
    EnzymeProvisioningPolicy,
)
from hop_design.models.physical import Strand
from hop_design.models.sequence import normalize_dna_sequence

from .basal_release import BasalFutureReleaseRequirement
from .complete.accounting import CompositionEnumerationPolicy
from .complete.request import ReleaseSideRequirement, TypeIisReleaseRequest, WholeRouteConstraints
from .complete.source_preparation import LinearSourceMaterializationSpec
from .components import ExactBasalArms
from .payload import (
    ConstructionEndpoint,
    FinalPayloadReference,
    LocalNeighborhoodFamily,
    RouteFamily,
)
from .product_pairing import (
    EndFootprintPairing,
    ProductConstraintConflict,
    require_proximal_match,
)
from .request import LocalNeighborhoodRequest
from .scaffold import constrain_foldback_geometry
from .search import BasalGeometryDomain, FoldbackGeometryDomain, NeighborhoodSearchPlan
from .source import ConstructionCompositionSource, ConstructionSource
from .source_partition.policy import SacrificialFragmentPolicy
from .targets import BasalPairConstraint, ConstructionConstraints, ConstructionPreferences


class ProductEnds(HopModel):
    """Required words, each read on its own protruding strand."""

    left: ReleaseSideRequirement
    right: ReleaseSideRequirement


class ProductFoldbackJob(HopModel):
    geometry: FoldbackGeometryDomain
    enzymes: EnzymePermissions
    search: NeighborhoodSearchPlan


class ProductBasalGeometry(BasalGeometryDomain):
    """End requirements belong to the product; this geometry cannot redeclare them."""

    future_release: None = Field(default=None, exclude=True)
    pairing_constraints: tuple[BasalPairConstraint, ...] = ()


class ProductBasalJob(HopModel):
    geometry: ProductBasalGeometry
    end_footprint_pairing: EndFootprintPairing | None = None
    enzymes: EnzymePermissions
    search: NeighborhoodSearchPlan


class ProductBasalReleaseProjection(HopModel):
    product_end: Literal["left", "right"]
    recognition_material: Literal["source_duplex", "endpoint_material"]


class ProductReleaseJob(HopModel):
    enzymes: EnzymePermissions
    max_site_pairs: int = Field(ge=1)
    basal_projection: ProductBasalReleaseProjection


class ProductRequest(HopModel):
    """Exact linear-source product intent, before discovery or method verification."""

    schema_id: Literal["hop.product-request/v1"] = Field(alias="schema")
    name: str | None = None
    stem_arm: str
    endpoint: ConstructionEndpoint
    ends: ProductEnds | None = None
    foldback: ProductFoldbackJob
    basal: ProductBasalJob | None = None
    hairpin_basal_component: ExactBasalArms | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    release: ProductReleaseJob | None = None
    enzyme_catalog: CharacterizedEnzymeCatalog
    materialization: LinearSourceMaterializationSpec
    local_constraints: ConstructionConstraints
    preferences: ConstructionPreferences = ConstructionPreferences()
    whole_route_constraints: WholeRouteConstraints
    enumeration: CompositionEnumerationPolicy
    source_cleanup: SacrificialFragmentPolicy | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @field_validator("stem_arm")
    @classmethod
    def normalize_stem(cls, value: str) -> str:
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_endpoint(self) -> ProductRequest:
        if (self.materialization.adapter_ligation is not None) != (
            self.endpoint is ConstructionEndpoint.ADAPTER_LIGATED_HAIRPIN
        ):
            raise ValueError("adapter_ligation is required only for an adapter-ligated hairpin.")
        if (
            self.hairpin_basal_component is not None
            and self.endpoint is not ConstructionEndpoint.SSDNA_HAIRPIN
        ):
            raise ValueError("A hairpin_basal_component is only valid for the hairpin endpoint.")
        if self.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
            if self.ends is None or self.release is None:
                raise ValueError(
                    "A released insert requires both oriented ends and release permissions."
                )
        elif self.ends is not None or self.release is not None:
            raise ValueError("Earlier endpoints must omit downstream ends and release permissions.")
        if self.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            if self.basal is not None:
                raise ValueError("A hairpin endpoint must omit downstream basal discovery.")
        elif self.basal is None:
            raise ValueError("A PCR-bearing endpoint requires basal geometry and permissions.")
        return self

    def _has_source_end_frame(self) -> bool:
        """Locate source contacts independently of recognition-site ownership."""
        if self.basal is None or self.release is None or self.ends is None:
            return False
        geometry = self.basal.geometry
        projection = self.release.basal_projection
        return (
            geometry.nick_strand is Strand.BOTTOM
            and len(geometry.nick_offsets_nt) == 1
            and projection.product_end == "right"
        )

    def source_end_footprint(self) -> tuple[tuple[int, str], ...]:
        """Project a required left end only where one authored basal frame fixes it."""
        if not self._has_source_end_frame():
            return ()
        assert self.basal is not None and self.ends is not None
        geometry = self.basal.geometry
        requirement = BasalFutureReleaseRequirement.model_validate_json(
            json.dumps(
                {
                    **self.ends.left.model_dump(mode="json"),
                    "product_end": "left",
                    "recognition_material": "source_duplex",
                }
            )
        )
        return tuple(
            sorted(requirement.source_contact_bases(nick_offset_nt=geometry.nick_offsets_nt[0]))
        )

    def expanded_pairing_constraints(self) -> tuple[BasalPairConstraint, ...]:
        if self.basal is None:
            return ()
        contacts = self.basal.geometry.pairing_constraints
        if self.basal.end_footprint_pairing is not None:
            if not self._has_source_end_frame():
                raise ValueError(
                    "End-footprint pairing requires a uniquely mapped left source end."
                )
            contacts = self.basal.end_footprint_pairing.expand(
                self.source_end_footprint(), contacts
            )
        if not contacts:
            raise ValueError(
                "Basal pairing requires absolute constraints or end_footprint_pairing."
            )
        return require_proximal_match(contacts)

    def implied_source_contact_bases(self) -> tuple[tuple[int, str], ...]:
        """Restrict only source positions covered by explicitly declared permissions."""
        declared = {item.position_from_ligation for item in self.expanded_pairing_constraints()}
        return tuple((p, base) for p, base in self.source_end_footprint() if p in declared)

    def _foldback_geometry(self) -> FoldbackGeometryDomain:
        return constrain_foldback_geometry(
            self.foldback.geometry,
            maximum=self.foldback.search.max_retained_overhead_nt,
            requirements=self.whole_route_constraints.hairpin_scaffold,
        )

    def construction_source(self) -> ConstructionSource:
        """Translate declarations without discovering, ranking, or relaxing requirements."""
        payload = FinalPayloadReference.model_validate(
            {
                "display_name": self.name,
                "payload": {"kind": "exact", "sequence": self.stem_arm},
                "basal_boundary": {"offset": 0},
                "foldback_boundary": {"offset": len(self.stem_arm)},
            }
        )

        def provision(permissions: EnzymePermissions) -> EnzymeProvisioningPolicy:
            return EnzymeProvisioningPolicy(**permissions.model_dump(), catalog=self.enzyme_catalog)

        def local(
            job: ProductFoldbackJob | ProductBasalJob,
            family: LocalNeighborhoodFamily,
            geometry: FoldbackGeometryDomain | BasalGeometryDomain,
        ) -> LocalNeighborhoodRequest:
            return LocalNeighborhoodRequest(
                name=None if self.name is None else f"{self.name}/{family.value}",
                payload=payload,
                family=family,
                route_family=RouteFamily.LINEAR_SOURCE_V1,
                endpoint=(
                    ConstructionEndpoint.SSDNA_HAIRPIN
                    if family is LocalNeighborhoodFamily.FOLDBACK
                    else self.endpoint
                ),
                geometry_domain=geometry,
                enzyme_provisioning=provision(job.enzymes),
                search=job.search,
                hard_constraints=self.local_constraints,
                preferences=self.preferences,
            )

        geometry = None
        release = None
        if self.basal is not None:
            geometry = {
                **self.basal.geometry.model_dump(),
                "pairing_constraints": tuple(
                    item.model_dump() for item in self.expanded_pairing_constraints()
                ),
            }
        if self.release is not None and self.ends is not None:
            assert geometry is not None
            implied = dict(self.implied_source_contact_bases())
            for contact in geometry["pairing_constraints"]:
                position = contact["position_from_ligation"]
                if position in implied:
                    base = implied[position]
                    if base not in contact["allowed_source_bases"]:
                        raise ProductConstraintConflict(
                            "Required left end conflicts with basal source base permissions "
                            f"at position {position} from ligation.",
                            code="end_source_base_conflict",
                            position_from_ligation=position,
                        )
                    contact["allowed_source_bases"] = (base,)
            geometry["future_release"] = {
                **getattr(self.ends, self.release.basal_projection.product_end).model_dump(),
                **self.release.basal_projection.model_dump(),
            }
            release = TypeIisReleaseRequest(
                left=self.ends.left,
                right=self.ends.right,
                enzyme_provisioning=provision(self.release.enzymes),
                max_site_pairs=self.release.max_site_pairs,
            )
        basal = None
        if self.basal is not None:
            basal = local(
                self.basal,
                LocalNeighborhoodFamily.BASAL,
                BasalGeometryDomain.model_validate(geometry),
            )
        # Reuse immutable inputs; validate every newly derived contract and the
        # complete route. External JSON admission still parses the full catalog.
        return ConstructionSource.model_validate(
            {
                "schema": "hop.construction-source/v8",
                "foldback": local(
                    self.foldback, LocalNeighborhoodFamily.FOLDBACK, self._foldback_geometry()
                ),
                "basal": basal,
                "composition": ConstructionCompositionSource(
                    endpoint=self.endpoint,
                    materialization=self.materialization,
                    release=release,
                    whole_route_constraints=self.whole_route_constraints,
                    enumeration=self.enumeration,
                ),
            }
        )
