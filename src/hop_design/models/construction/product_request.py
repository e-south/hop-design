"""Author one product intent and expand only into existing molecular contracts."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import CharacterizedEnzymeCatalog, EnzymePermissions
from hop_design.models.physical import Strand
from hop_design.models.sequence import normalize_dna_sequence

from .basal_release import BasalFutureReleaseRequirement
from .complete.accounting import CompositionEnumerationPolicy
from .complete.request import ReleaseSideRequirement, WholeRouteConstraints
from .complete.source_preparation import LinearSourceMaterializationSpec
from .components import ExactBasalArms
from .payload import ConstructionEndpoint
from .product_pairing import (
    EndFootprintPairing,
    ProductConstraintConflict,
    require_proximal_match,
)
from .scaffold import constrain_foldback_geometry
from .search import BasalGeometryDomain, FoldbackGeometryDomain, NeighborhoodSearchPlan
from .source import ConstructionSource
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

    def _foldback_geometry(self) -> dict[str, object]:
        return constrain_foldback_geometry(
            self.foldback.geometry,
            maximum=self.foldback.search.max_retained_overhead_nt,
            requirements=self.whole_route_constraints.hairpin_scaffold,
        ).model_dump(mode="json")

    def construction_source(self) -> ConstructionSource:
        """Translate declarations without discovering, ranking, or relaxing requirements."""
        catalog = self.enzyme_catalog.model_dump(mode="json", by_alias=True)
        payload: dict[str, object] = {
            "schema": "hop.final-payload/v1",
            "display_name": self.name,
            "payload": {"kind": "exact", "sequence": self.stem_arm},
            "basal_boundary": {"offset": 0},
            "foldback_boundary": {"offset": len(self.stem_arm)},
            "pair_state_exceptions": [],
        }

        def local(job: ProductFoldbackJob | ProductBasalJob, family: str) -> dict[str, object]:
            return {
                "schema": "hop.local-neighborhood-request/v7",
                "name": None if self.name is None else f"{self.name}/{family}",
                "payload": payload,
                "family": family,
                "route_family": "linear_source/v1",
                "endpoint": "ssdna_hairpin" if family == "foldback" else self.endpoint.value,
                "geometry_domain": (
                    self._foldback_geometry()
                    if family == "foldback"
                    else job.geometry.model_dump(mode="json")
                ),
                "enzyme_provisioning": {**job.enzymes.model_dump(mode="json"), "catalog": catalog},
                "search": job.search.model_dump(mode="json"),
                "hard_constraints": self.local_constraints.model_dump(mode="json"),
                "preferences": self.preferences.model_dump(mode="json"),
            }

        basal = None if self.basal is None else local(self.basal, "basal")
        release = None
        if basal is not None:
            assert self.basal is not None
            basal["geometry_domain"] = {
                **self.basal.geometry.model_dump(mode="json"),
                "pairing_constraints": [
                    item.model_dump(mode="json") for item in self.expanded_pairing_constraints()
                ],
            }
        if self.release is not None and self.ends is not None:
            assert basal is not None and self.basal is not None
            ends = self.ends.model_dump(mode="json")
            projection = self.release.basal_projection.model_dump(mode="json")
            geometry = dict(self.basal.geometry.model_dump(mode="json"))
            geometry["pairing_constraints"] = [
                item.model_dump(mode="json") for item in self.expanded_pairing_constraints()
            ]
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
                    contact["allowed_source_bases"] = [base]
            geometry["future_release"] = {
                **ends[self.release.basal_projection.product_end],
                **projection,
            }
            basal["geometry_domain"] = geometry
            release = {
                **ends,
                "enzyme_provisioning": {
                    **self.release.enzymes.model_dump(mode="json"),
                    "catalog": catalog,
                },
                "max_site_pairs": self.release.max_site_pairs,
            }
        source = {
            "schema": "hop.construction-source/v8",
            "foldback": local(self.foldback, "foldback"),
            "basal": basal,
            "composition": {
                "endpoint": self.endpoint.value,
                "materialization": self.materialization.model_dump(mode="json"),
                "release": release,
                "whole_route_constraints": self.whole_route_constraints.model_dump(mode="json"),
                "enumeration": self.enumeration.model_dump(mode="json"),
            },
        }
        # Existing contracts remain the authority for role permissions, endpoint
        # obligations, material chemistry, geometry and bounded execution.
        return ConstructionSource.model_validate_json(json.dumps(source))
