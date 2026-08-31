"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/request.py

Defines exact materialization inputs and bounded complete-route requests.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Literal, cast

from pydantic import (
    Field,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    field_validator,
    model_serializer,
    model_validator,
)

from hop_design.models.base import HopModel
from hop_design.models.bundle import HopBundle, validate_bundle_manifest
from hop_design.models.construction.payload import (
    ConstructionEndpoint,
    FinalPayloadReference,
    RouteFamily,
    _content_id,
)
from hop_design.models.enzymes import EnzymeClass, EnzymeProvisioningPolicy, EnzymeRole
from hop_design.models.molecular_state import EndChemistry, StrandEnd
from hop_design.models.physical import SiteOrientation
from hop_design.models.plan import HopPlan
from hop_design.models.sequence import normalize_dna_sequence
from hop_design.models.spec import DesignAuthoritySpec
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .accounting import CompositionEnumerationPolicy

_DESIGN_SPEC_ADAPTER: TypeAdapter[DesignAuthoritySpec] = TypeAdapter(DesignAuthoritySpec)


class MaterialOrigin(StrEnum):
    """Caller-declared physical origin of one exact route material."""

    SYNTHESIZED = "synthesized"
    PCR_DERIVED = "pcr_derived"
    PURIFIED = "purified"


class ExactConstructionMaterial(HopModel):
    """One exact caller-owned material including terminal chemistry."""

    material_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    origin: MaterialOrigin
    sequence_5prime: str
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry

    @field_validator("sequence_5prime", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Construction material sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)


class PcrPrimer(HopModel):
    """One exact oligo with a terminal three-prime annealing segment."""

    oligo: ExactConstructionMaterial
    annealing_length_nt: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_annealing_length(self) -> PcrPrimer:
        if self.annealing_length_nt > len(self.oligo.sequence_5prime):
            raise ValueError("Primer annealing length cannot exceed the exact oligo length.")
        return self

    @property
    def annealing_sequence(self) -> str:
        """Return the terminal three-prime segment that binds the template."""
        return self.oligo.sequence_5prime[-self.annealing_length_nt :]

    @property
    def five_prime_handle(self) -> str:
        """Return exact primer sequence outside the terminal annealing segment."""
        return self.oligo.sequence_5prime[: -self.annealing_length_nt]


class ReleaseSideRequirement(HopModel):
    """One oriented cohesive-end requirement at a clone endpoint side."""

    orientation: SiteOrientation
    cohesive_end_sequence: str
    overhang_end: StrandEnd

    @field_validator("cohesive_end_sequence", mode="before")
    @classmethod
    def normalize_cohesive_end(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Cohesive-end sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)


class TypeIisReleaseRequest(HopModel):
    """Caller-provisioned bounded search for one oriented Type IIS site pair."""

    enzyme_provisioning: EnzymeProvisioningPolicy
    left: ReleaseSideRequirement
    right: ReleaseSideRequirement
    max_site_pairs: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_release_policy(self) -> TypeIisReleaseRequest:
        candidates = tuple(
            enzyme
            for enzyme in self.enzyme_provisioning.catalog.enzymes
            if self.enzyme_provisioning.permits(
                enzyme.enzyme_id,
                role=EnzymeRole.END_GENERATION,
            )
        )
        if len(candidates) != 1:
            raise ValueError(
                "Type IIS release requires exactly one provisioned end-generation enzyme."
            )
        if any(enzyme.enzyme_class is not EnzymeClass.DUPLEX_RESTRICTION for enzyme in candidates):
            raise ValueError("Type IIS release requires duplex restriction enzymes.")
        enzyme = candidates[0]
        complement_offset = enzyme.cut_offset_complement_strand
        if complement_offset is None or not (
            (
                enzyme.cut_offset_reference_strand >= enzyme.recognition_length
                and complement_offset >= enzyme.recognition_length
            )
            or (enzyme.cut_offset_reference_strand <= 0 and complement_offset <= 0)
        ):
            raise ValueError("A Type IIS release enzyme must cleave outside its recognition site.")
        return self


class LinearSourceMaterializationSpec(HopModel):
    """Source origin/chemistry policy plus exact endpoint-dependent auxiliary oligos."""

    source_origin: MaterialOrigin
    source_five_prime_end: EndChemistry
    source_three_prime_end: EndChemistry
    source_complement_origin: MaterialOrigin
    source_complement_five_prime_end: EndChemistry
    source_complement_three_prime_end: EndChemistry
    adapter: ExactConstructionMaterial | None = None
    forward_primer: PcrPrimer | None = None
    reverse_primer: PcrPrimer | None = None

    @model_validator(mode="after")
    def validate_unique_auxiliaries(self) -> LinearSourceMaterializationSpec:
        materials = tuple(
            item
            for item in (
                self.adapter,
                None if self.forward_primer is None else self.forward_primer.oligo,
                None if self.reverse_primer is None else self.reverse_primer.oligo,
            )
            if item is not None
        )
        ids = tuple(item.material_id for item in materials)
        if len(ids) != len(set(ids)):
            raise ValueError("Construction material ids must be unique.")
        return self


class DesignAuthorityReference(HopModel):
    """Exact verified-design relation required by whole-route composition."""

    bundle: HopBundle
    spec: DesignAuthoritySpec
    plan: HopPlan
    plan_id: str = Field(min_length=1)
    design_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    payload_sequence: str
    encoding_sequence: str
    encoding_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("payload_sequence", "encoding_sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Design-authority sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_digest(self) -> DesignAuthorityReference:
        plan = HopPlan.model_validate(self.plan.model_dump(mode="python"))
        spec = _DESIGN_SPEC_ADAPTER.validate_python(self.spec.model_dump(mode="python"))
        validate_bundle_manifest(self.bundle)
        spec_digest = sha256_digest(canonical_json_bytes(spec))
        observed = f"sha256:{hashlib.sha256(self.encoding_sequence.encode()).hexdigest()}"
        if self.encoding_digest != observed:
            raise ValueError("Design-authority encoding digest must match its exact sequence.")
        encoding = plan.hairpin_encoding_insert
        if (
            plan.plan_id != self.plan_id
            or plan.design_id != self.design_id
            or self.bundle.design_id != self.design_id
            or self.bundle.spec_digest != spec_digest
            or self.bundle.external_refs != spec.external_refs
            or self.bundle.plan_digest != sha256_digest(canonical_json_bytes(plan))
            or spec.design_id != self.design_id
            or spec.payload.sequence != self.payload_sequence
            or plan.spec_digest != spec_digest
            or plan.payload_sequence != self.payload_sequence
            or plan.lock.defaults_ref != spec.defaults_ref
            or plan.lock.constraint_profile_ref != spec.constraint_profile_ref
            or plan.lock.design_derivation_ref != spec.design_derivation_ref
            or encoding.sequence != self.encoding_sequence
            or encoding.sequence_digest != self.encoding_digest
        ):
            raise ValueError(
                "Design authority must bind the exact authored design specification "
                "and model-layer HOP plan."
            )
        return self


class WholeRouteConstraints(HopModel):
    """Fail-closed constraints applied to every complete local combination."""

    preserve_payload: Literal[True] = True
    reject_unintended_actionable_sites: Literal[True] = True
    require_exact_materials: Literal[True] = True
    require_all_combinations_valid: bool = False


class ConstructionDiscoveryRequest(HopModel):
    """Exact payload, local authorities, materials, endpoint, and design relation."""

    schema_id: Literal["hop.construction-discovery-request/v3"] = Field(
        default="hop.construction-discovery-request/v3", alias="schema"
    )
    payload: FinalPayloadReference
    route_family: RouteFamily
    endpoint: ConstructionEndpoint
    foldback_intermediate_endpoint: ConstructionEndpoint = ConstructionEndpoint.SSDNA_HAIRPIN
    foldback_result_id: str = Field(pattern=r"^hop:foldback-neighborhood-result/[0-9a-f]{64}@1$")
    basal_result_id: str | None = Field(
        default=None,
        pattern=r"^hop:basal-neighborhood-result/[0-9a-f]{64}@1$",
    )
    selected_foldback_realization_id: str | None = Field(
        default=None,
        pattern=r"^hop:foldback-realization/[0-9a-f]{64}@1$",
    )
    selected_basal_realization_id: str | None = Field(
        default=None,
        pattern=r"^hop:basal-realization/[0-9a-f]{64}@1$",
    )
    materialization: LinearSourceMaterializationSpec
    release: TypeIisReleaseRequest | None = None
    design: DesignAuthorityReference
    whole_route_constraints: WholeRouteConstraints
    enumeration: CompositionEnumerationPolicy

    @model_serializer(mode="wrap")
    def serialize_request(
        self,
        handler: SerializerFunctionWrapHandler,
    ) -> dict[str, object]:
        content = cast(dict[str, object], handler(self))
        if not self.selects_local_pair:
            content.pop("selected_foldback_realization_id", None)
            content.pop("selected_basal_realization_id", None)
        return content

    @model_validator(mode="after")
    def validate_endpoint_materials(self) -> ConstructionDiscoveryRequest:
        DesignAuthorityReference.model_validate(self.design.model_dump(mode="python"))
        if self.design.payload_sequence != self.payload.payload.sequence:
            raise ValueError("Design authority must bind the exact requested payload.")
        if self.foldback_intermediate_endpoint is not ConstructionEndpoint.SSDNA_HAIRPIN:
            raise ValueError("The foldback intermediate must be an ssDNA hairpin.")
        auxiliaries = (
            self.materialization.adapter,
            self.materialization.forward_primer,
            self.materialization.reverse_primer,
        )
        if self.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            if any(item is not None for item in auxiliaries) or self.release is not None:
                raise ValueError("A direct endpoint must omit adapter and PCR primers.")
        elif self.basal_result_id is None or any(item is None for item in auxiliaries):
            raise ValueError(
                "PCR-bearing endpoints require an exact adapter and both primers "
                "plus basal authority."
            )
        elif self.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            if self.release is not None:
                raise ValueError("A hairpin PCR endpoint must omit clone release.")
        elif self.release is None:
            raise ValueError("A clone-ready endpoint requires exact Type IIS release.")
        if (self.selected_foldback_realization_id is None) != (
            self.selected_basal_realization_id is None
        ):
            raise ValueError("Selected composition requires both local realization ids.")
        if self.selects_local_pair and self.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            raise ValueError("Selected-pair composition requires a PCR-bearing endpoint.")
        return self

    @property
    def selects_local_pair(self) -> bool:
        """Return whether composition is restricted to one explicit local pair."""
        return self.selected_foldback_realization_id is not None

    @property
    def problem_id(self) -> str:
        """Return scientific identity excluding presentation and execution policy."""
        content = {
            "payload_spec_id": self.payload.payload_spec_id,
            "route_family": self.route_family,
            "endpoint": self.endpoint,
            "foldback_intermediate_endpoint": self.foldback_intermediate_endpoint,
            "foldback_result_id": self.foldback_result_id,
            "basal_result_id": self.basal_result_id,
            "materialization": self.materialization.model_dump(mode="json"),
            "release": None if self.release is None else self.release.model_dump(mode="json"),
            "design": self.design.model_dump(mode="json"),
            "whole_route_constraints": self.whole_route_constraints.model_dump(mode="json"),
        }
        if self.selects_local_pair:
            content["selected_foldback_realization_id"] = self.selected_foldback_realization_id
            content["selected_basal_realization_id"] = self.selected_basal_realization_id
        return _content_id("construction-problem", 1, content)

    @property
    def request_id(self) -> str:
        """Return content identity over the complete construction request."""
        return _content_id("construction-request", 1, self.model_dump(mode="json"))


__all__ = [
    "ConstructionDiscoveryRequest",
    "DesignAuthorityReference",
    "ExactConstructionMaterial",
    "LinearSourceMaterializationSpec",
    "MaterialOrigin",
    "PcrPrimer",
    "ReleaseSideRequirement",
    "TypeIisReleaseRequest",
    "WholeRouteConstraints",
]
