"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction.py

Defines payload-centered construction requests, identities, results, and groupings.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Literal, cast

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    EnzymeProvisioningPolicy,
    characterized_enzyme_catalog_digest,
)
from hop_design.models.junction import Strand
from hop_design.models.payload import Payload
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import (
    iupac_bases,
    normalize_dna_sequence,
    reverse_complement_iupac,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest


class RouteFamily(StrEnum):
    """Implemented source-realization route families."""

    LINEAR_SOURCE_V1 = "linear_source/v1"


class ConstructionEndpoint(StrEnum):
    """Requested molecular endpoint of a construction route."""

    SSDNA_HAIRPIN = "ssdna_hairpin"
    HAIRPIN_PCR_DUPLEX = "hairpin_pcr_duplex"
    CLONE_READY_DUPLEX = "clone_ready_duplex"


class LocalNeighborhoodFamily(StrEnum):
    """Payload-boundary neighborhood families."""

    FOLDBACK = "foldback"
    BASAL = "basal"


class SourceOrientation(StrEnum):
    """Orientation of a final-payload segment in one route-owned source."""

    FORWARD = "forward"
    REVERSE_COMPLEMENT = "reverse_complement"


class PairState(HopModel):
    """One allowed correlated base pair at a final-payload position."""

    reference_base: str
    paired_base: str

    @field_validator("reference_base", "paired_base", mode="before")
    @classmethod
    def normalize_base(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Pair-state bases must be DNA strings.")
        sequence = normalize_dna_sequence(value, allow_degenerate=False)
        if len(sequence) != 1:
            raise ValueError("Pair-state bases must contain exactly one nucleotide.")
        return sequence


class PairStateException(HopModel):
    """Allowed correlated pair states that replace derived complementarity at one position."""

    payload_position: int = Field(ge=0)
    allowed_states: tuple[PairState, ...] = Field(min_length=1)

    @field_validator("allowed_states", mode="after")
    @classmethod
    def canonicalize_states(cls, values: tuple[PairState, ...]) -> tuple[PairState, ...]:
        return tuple(sorted(values, key=lambda item: (item.reference_base, item.paired_base)))

    @model_validator(mode="after")
    def validate_states(self) -> PairStateException:
        if len(self.allowed_states) != len(set(self.allowed_states)):
            raise ValueError("Pair-state exceptions must not repeat an allowed state.")
        return self


def _content_id(kind: str, version: int, value: object) -> str:
    digest = sha256_digest(canonical_json_bytes(value)).removeprefix("sha256:")
    return f"hop:{kind}/{digest}@{version}"


class FinalPayloadReference(HopModel):
    """One authored final payload with derived pairing and explicit endpoint boundaries."""

    schema_id: Literal["hop.final-payload/v1"] = Field(
        default="hop.final-payload/v1", alias="schema"
    )
    display_name: str | None = None
    payload: Payload
    basal_boundary: Boundary
    foldback_boundary: Boundary
    pair_state_exceptions: tuple[PairStateException, ...] = ()

    @field_validator("pair_state_exceptions", mode="after")
    @classmethod
    def canonicalize_pair_state_exceptions(
        cls, values: tuple[PairStateException, ...]
    ) -> tuple[PairStateException, ...]:
        return tuple(sorted(values, key=lambda item: item.payload_position))

    @model_validator(mode="after")
    def validate_payload_coordinates(self) -> FinalPayloadReference:
        payload_length = len(self.payload.sequence)
        if self.basal_boundary.offset != 0:
            raise ValueError("The basal boundary must be the start of the final payload.")
        if self.foldback_boundary.offset != payload_length:
            raise ValueError("The foldback boundary must be the end of the final payload.")
        positions = tuple(item.payload_position for item in self.pair_state_exceptions)
        if len(positions) != len(set(positions)):
            raise ValueError("Pair-state exception positions must be unique.")
        if any(position >= payload_length for position in positions):
            raise ValueError("Pair-state exception positions must lie within the final payload.")
        for exception in self.pair_state_exceptions:
            authored_domain = iupac_bases(self.payload.sequence[exception.payload_position])
            if any(
                state.reference_base not in authored_domain for state in exception.allowed_states
            ):
                raise ValueError(
                    "Pair-state reference bases must lie within the authored payload domain."
                )
        return self

    @property
    def paired_sequence(self) -> str:
        """Return the normally derived reverse-complement arm."""
        return self.payload.paired_sequence

    @property
    def payload_spec_id(self) -> str:
        """Return molecular identity independent of presentation metadata."""
        return _content_id(
            "payload-spec",
            1,
            {
                "schema": self.schema_id,
                "payload": self.payload.model_dump(mode="json"),
                "basal_boundary": self.basal_boundary.model_dump(mode="json"),
                "foldback_boundary": self.foldback_boundary.model_dump(mode="json"),
                "pair_state_exceptions": tuple(
                    {
                        "payload_position": item.payload_position,
                        "allowed_states": tuple(
                            state.model_dump(mode="json")
                            for state in sorted(
                                item.allowed_states,
                                key=lambda state: (
                                    state.reference_base,
                                    state.paired_base,
                                ),
                            )
                        ),
                    }
                    for item in sorted(
                        self.pair_state_exceptions,
                        key=lambda exception: exception.payload_position,
                    )
                ),
            },
        )


class PayloadSourceSegment(HopModel):
    """Mapping of one final-payload span into one route-owned source material."""

    payload_span: Span
    source_material_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    source_span: Span
    orientation: SourceOrientation

    @model_validator(mode="after")
    def validate_equal_lengths(self) -> PayloadSourceSegment:
        if self.payload_span.length.value != self.source_span.length.value:
            raise ValueError("Payload and source spans must have equal lengths.")
        if self.payload_span.length.value == 0:
            raise ValueError("Payload-to-source segments must not be empty.")
        return self


class PayloadSourceMap(HopModel):
    """Route-owned mapping that can represent contiguous or segmented payload encoding."""

    segments: tuple[PayloadSourceSegment, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_payload_spans(self) -> PayloadSourceMap:
        ordered = sorted(
            self.segments,
            key=lambda segment: (
                segment.payload_span.start.offset,
                segment.payload_span.end.offset,
            ),
        )
        for previous, current in pairwise(ordered):
            if previous.payload_span.end.offset > current.payload_span.start.offset:
                raise ValueError("Payload-to-source segments must not overlap.")
        return self


def validate_linear_source_payload(payload: FinalPayloadReference) -> None:
    """Reject payload features unsupported by the current linear-source route."""
    if payload.pair_state_exceptions:
        raise ValueError("linear_source/v1 does not support pair-state exceptions.")


def validate_linear_source_map(
    payload: FinalPayloadReference,
    source_map: PayloadSourceMap,
) -> None:
    """Require the current route's one contiguous forward payload encoding."""
    if len(source_map.segments) != 1:
        raise ValueError("linear_source/v1 requires one contiguous source segment.")
    segment = source_map.segments[0]
    expected = Span(start=payload.basal_boundary, end=payload.foldback_boundary)
    if segment.payload_span != expected:
        raise ValueError("The linear source segment must cover the complete final payload.")
    if segment.orientation is not SourceOrientation.FORWARD:
        raise ValueError("linear_source/v1 requires a forward payload source segment.")


class FoldbackTarget(HopModel):
    """Requested retained foldback geometry in final-payload coordinates."""

    family: Literal["foldback"] = "foldback"
    junction_offset_nt: int = Field(ge=0)
    loop_length_nt: int = Field(ge=1)
    annealing_arm_length_bp: int = Field(ge=1)


class BasalPairClass(StrEnum):
    """Construction bookkeeping for one basal source-adapter pair."""

    MATCH = "match"
    WOBBLE = "wobble"
    MISMATCH = "mismatch"


class BasalPairingPosition(HopModel):
    """One payload-proximal-to-outward basal pairing position."""

    profile_position: int = Field(ge=0)
    source_base: str
    adapter_base: str
    pair_class: BasalPairClass

    @field_validator("source_base", "adapter_base", mode="before")
    @classmethod
    def normalize_base(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Basal pairing bases must be DNA strings.")
        sequence = normalize_dna_sequence(value, allow_degenerate=False)
        if len(sequence) != 1:
            raise ValueError("Basal pairing bases must contain exactly one nucleotide.")
        return sequence

    @model_validator(mode="after")
    def validate_pair_class(self) -> BasalPairingPosition:
        is_match = reverse_complement_iupac(self.source_base) == self.adapter_base
        if (self.pair_class is BasalPairClass.MATCH) != is_match:
            raise ValueError("Basal match classification must reflect Watson-Crick pairing.")
        return self


class EndGenerationRequest(HopModel):
    """Optional exact or discoverable end geometry for a clone-ready endpoint."""

    type_iis_cut_offset_nt: int = Field(ge=0)
    requested_overhangs: tuple[str, ...] = ()

    @field_validator("requested_overhangs", mode="before")
    @classmethod
    def normalize_overhangs(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("Requested overhangs must be a sequence collection.")
        return tuple(
            sorted(normalize_dna_sequence(overhang, allow_degenerate=False) for overhang in value)
        )

    @model_validator(mode="after")
    def validate_overhangs(self) -> EndGenerationRequest:
        if len(self.requested_overhangs) != len(set(self.requested_overhangs)):
            raise ValueError("Requested overhangs must be unique.")
        return self


class BasalTarget(HopModel):
    """Endpoint-dependent basal nick, pairing, and optional end-generation target."""

    family: Literal["basal"] = "basal"
    nick_strand: Strand
    nick_offset_nt: int = Field(ge=0)
    pairing_profile: tuple[BasalPairingPosition, ...] = ()
    ligation_proximal_match_required: bool = False
    end_generation: EndGenerationRequest | None = None

    @model_validator(mode="after")
    def validate_pairing_profile(self) -> BasalTarget:
        positions = tuple(item.profile_position for item in self.pairing_profile)
        if positions != tuple(range(len(positions))):
            raise ValueError("Basal pairing positions must be contiguous from the payload outward.")
        if (
            self.ligation_proximal_match_required
            and self.pairing_profile
            and self.pairing_profile[0].pair_class is not BasalPairClass.MATCH
        ):
            raise ValueError("The payload-proximal basal pair must be a match.")
        return self


LocalGeometryTarget = Annotated[FoldbackTarget | BasalTarget, Field(discriminator="family")]


class ConstructionConstraints(HopModel):
    """Hard invariants shared by local construction discovery."""

    preserve_payload: Literal[True] = True
    forbid_unintended_actionable_sites: Literal[True] = True


class ConstructionPreferences(HopModel):
    """Non-authoritative ordering preferences over already valid realizations."""

    retained_construction: Literal["compact"] = "compact"
    payload_compatibility: Literal["report"] = "report"
    ranking: Literal["none"] = "none"
    preferred_enzyme_ids: tuple[ReferenceId, ...] = ()

    @field_validator("preferred_enzyme_ids", mode="after")
    @classmethod
    def canonicalize_preferred_enzymes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Preferred enzyme ids must be unique.")
        return tuple(sorted(values))


class RelaxationMode(StrEnum):
    """Declared stopping semantics for discrete geometry relaxation."""

    EXACT_ONLY = "exact_only"
    FIRST_FEASIBLE_SHELL = "first_feasible_shell"
    THROUGH_RADIUS = "through_radius"


class RelaxationCoordinate(HopModel):
    """One explicitly enabled integer target coordinate and its hard bounds."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
    minimum: int
    maximum: int

    @model_validator(mode="after")
    def validate_bounds(self) -> RelaxationCoordinate:
        if self.maximum < self.minimum:
            raise ValueError("Relaxation-coordinate maximum must not precede its minimum.")
        return self


class RelaxationPolicy(HopModel):
    """Exact-first discrete relaxation with explicit enabled coordinates."""

    mode: RelaxationMode
    max_radius: int = Field(ge=0)
    coordinates: tuple[RelaxationCoordinate, ...] = ()

    @field_validator("coordinates", mode="after")
    @classmethod
    def canonicalize_coordinates(
        cls, values: tuple[RelaxationCoordinate, ...]
    ) -> tuple[RelaxationCoordinate, ...]:
        return tuple(sorted(values, key=lambda item: item.name))

    @model_validator(mode="after")
    def validate_policy(self) -> RelaxationPolicy:
        names = tuple(coordinate.name for coordinate in self.coordinates)
        if len(names) != len(set(names)):
            raise ValueError("Relaxation-coordinate names must be unique.")
        if self.mode is RelaxationMode.EXACT_ONLY and self.max_radius != 0:
            raise ValueError("exact_only relaxation requires max_radius=0.")
        if self.max_radius > 0 and not self.coordinates:
            raise ValueError("A positive relaxation radius requires enabled coordinates.")
        return self


class EnumerationPolicy(HopModel):
    """Finite execution limits that do not change the scientific problem identity."""

    max_search_nodes: int = Field(ge=1)
    max_realizations: int = Field(ge=1)


def geometry_coordinate_value(target: LocalGeometryTarget, coordinate_name: str) -> int:
    """Resolve one integer geometry coordinate, including declared nested fields."""
    current: object = target
    for field_name in coordinate_name.split("."):
        if not isinstance(current, HopModel) or field_name not in type(current).model_fields:
            raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
        current = getattr(current, field_name)
    if not isinstance(current, int) or isinstance(current, bool):
        raise ValueError(f"Relaxation coordinate {coordinate_name} must be an integer.")
    return current


def geometry_with_coordinate_value(
    target: LocalGeometryTarget,
    coordinate_name: str,
    value: int,
) -> LocalGeometryTarget:
    """Return one target copy with a declared integer coordinate replaced."""

    def replace(model: HopModel, path: tuple[str, ...]) -> HopModel:
        field_name, *remaining = path
        if field_name not in type(model).model_fields:
            raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
        if not remaining:
            return model.model_copy(update={field_name: value})
        child = getattr(model, field_name)
        if not isinstance(child, HopModel):
            raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
        return model.model_copy(update={field_name: replace(child, tuple(remaining))})

    return cast(LocalGeometryTarget, replace(target, tuple(coordinate_name.split("."))))


def geometry_fixed_projection(
    target: LocalGeometryTarget,
    relaxed_coordinate_names: set[str],
) -> dict[str, object]:
    """Return geometry content with explicitly relaxed leaves removed."""
    projection = target.model_dump(mode="json")
    for coordinate_name in relaxed_coordinate_names:
        cursor: object = projection
        parts = coordinate_name.split(".")
        for field_name in parts[:-1]:
            if not isinstance(cursor, dict) or field_name not in cursor:
                raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
            cursor = cursor[field_name]
        if not isinstance(cursor, dict) or parts[-1] not in cursor:
            raise ValueError(f"Unknown relaxation coordinate: {coordinate_name}.")
        del cursor[parts[-1]]
    return projection


class LocalNeighborhoodRequest(HopModel):
    """Shared payload-centered request envelope for foldback or basal discovery."""

    schema_id: Literal["hop.local-neighborhood-request/v1"] = Field(
        default="hop.local-neighborhood-request/v1", alias="schema"
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
            if target.pairing_profile or target.ligation_proximal_match_required:
                raise ValueError("ssdna_hairpin must not invent adapter-pairing requirements.")
            return
        if not target.pairing_profile:
            raise ValueError(f"{self.endpoint.value} requires a pairing profile.")
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


class ConstructionExecution(HopModel):
    """Replay identity for one bounded execution of a scientific construction problem."""

    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    hop_version: str
    route_implementation_version: str
    enumeration: EnumerationPolicy
    max_operations: int | None = Field(ge=1)
    environment: dict[str, str]

    @property
    def execution_id(self) -> str:
        """Return identity including implementation and replay-relevant execution facts."""
        return _content_id("execution", 1, self.model_dump(mode="json"))


class LocalRealization(HopModel):
    """One exact local sequence, enzyme binding, stage program, and achieved geometry."""

    local_realization_id: str = Field(pattern=r"^hop:local-realization/[0-9a-f]{64}@1$")
    local_sequence: str
    enzyme_binding_ids: tuple[str, ...]
    stage_ids: tuple[str, ...]
    achieved_geometry: LocalGeometryTarget

    @field_validator("local_sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Local realization sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @classmethod
    def create(
        cls,
        *,
        local_sequence: str,
        enzyme_binding_ids: tuple[str, ...],
        stage_ids: tuple[str, ...],
        achieved_geometry: LocalGeometryTarget,
    ) -> LocalRealization:
        """Create a content-addressed exact local realization."""
        content = {
            "local_sequence": normalize_dna_sequence(local_sequence, allow_degenerate=False),
            "enzyme_binding_ids": enzyme_binding_ids,
            "stage_ids": stage_ids,
            "achieved_geometry": achieved_geometry.model_dump(mode="json"),
        }
        return cls(
            local_realization_id=_content_id("local-realization", 1, content),
            local_sequence=local_sequence,
            enzyme_binding_ids=enzyme_binding_ids,
            stage_ids=stage_ids,
            achieved_geometry=achieved_geometry,
        )

    @model_validator(mode="after")
    def validate_identity(self) -> LocalRealization:
        expected = _content_id(
            "local-realization",
            1,
            {
                "local_sequence": self.local_sequence,
                "enzyme_binding_ids": self.enzyme_binding_ids,
                "stage_ids": self.stage_ids,
                "achieved_geometry": self.achieved_geometry.model_dump(mode="json"),
            },
        )
        if self.local_realization_id != expected:
            raise ValueError("local_realization_id must match the complete local realization.")
        return self


class FinalProductReference(HopModel):
    """Exact endpoint sequence, end descriptors, and topology."""

    final_product_id: str = Field(pattern=r"^hop:final-product/[0-9a-f]{64}@1$")
    endpoint: ConstructionEndpoint
    sequence: str
    topology: str
    end_descriptors: tuple[str, ...]

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Final product sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @classmethod
    def create(
        cls,
        *,
        endpoint: ConstructionEndpoint,
        sequence: str,
        topology: str,
        end_descriptors: tuple[str, ...],
    ) -> FinalProductReference:
        """Create a content-addressed exact final product reference."""
        content = {
            "endpoint": endpoint,
            "sequence": normalize_dna_sequence(sequence, allow_degenerate=False),
            "topology": topology,
            "end_descriptors": end_descriptors,
        }
        return cls(
            final_product_id=_content_id("final-product", 1, content),
            endpoint=endpoint,
            sequence=sequence,
            topology=topology,
            end_descriptors=end_descriptors,
        )

    @model_validator(mode="after")
    def validate_identity(self) -> FinalProductReference:
        expected = _content_id(
            "final-product",
            1,
            {
                "endpoint": self.endpoint,
                "sequence": self.sequence,
                "topology": self.topology,
                "end_descriptors": self.end_descriptors,
            },
        )
        if self.final_product_id != expected:
            raise ValueError("final_product_id must match the exact endpoint product.")
        return self


class CompleteConstructionRealization(HopModel):
    """One complete precursor, route trajectory, and exact endpoint product relation."""

    complete_realization_id: str = Field(pattern=r"^hop:complete-realization/[0-9a-f]{64}@1$")
    precursor_sequence: str
    local_realization_ids: tuple[str, ...] = Field(min_length=1)
    stage_ids: tuple[str, ...] = Field(min_length=1)
    final_product_id: str = Field(pattern=r"^hop:final-product/[0-9a-f]{64}@1$")

    @field_validator("precursor_sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Construction precursor must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @classmethod
    def create(
        cls,
        *,
        precursor_sequence: str,
        local_realization_ids: tuple[str, ...],
        stage_ids: tuple[str, ...],
        final_product_id: str,
    ) -> CompleteConstructionRealization:
        """Create a content-addressed complete route realization."""
        content = {
            "precursor_sequence": normalize_dna_sequence(
                precursor_sequence, allow_degenerate=False
            ),
            "local_realization_ids": local_realization_ids,
            "stage_ids": stage_ids,
            "final_product_id": final_product_id,
        }
        return cls(
            complete_realization_id=_content_id("complete-realization", 1, content),
            precursor_sequence=precursor_sequence,
            local_realization_ids=local_realization_ids,
            stage_ids=stage_ids,
            final_product_id=final_product_id,
        )

    @model_validator(mode="after")
    def validate_identity(self) -> CompleteConstructionRealization:
        expected = _content_id(
            "complete-realization",
            1,
            {
                "precursor_sequence": self.precursor_sequence,
                "local_realization_ids": self.local_realization_ids,
                "stage_ids": self.stage_ids,
                "final_product_id": self.final_product_id,
            },
        )
        if self.complete_realization_id != expected:
            raise ValueError("complete_realization_id must match the complete route relation.")
        return self


class SearchCompletionStatus(StrEnum):
    """Truthful disposition of one bounded scientific search."""

    COMPLETE = "complete"
    INFEASIBLE = "infeasible"
    TRUNCATED = "truncated"


class RelaxationShellSummary(HopModel):
    """Completion evidence and exact realization membership for one examined shell."""

    radius: int = Field(ge=0)
    examined: bool
    realization_ids: tuple[str, ...]


class FailureReasonCount(HopModel):
    """Stable aggregate count for one rejected-candidate or payload-conflict reason."""

    code: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,95}$")
    count: int = Field(ge=1)


class PayloadCompatibilityStatus(StrEnum):
    """Whether bounded payload compatibility was exhaustively calculated."""

    COMPLETE = "complete"
    NOT_COMPUTED = "not_computed"


class PayloadCompatibilityAccounting(HopModel):
    """Exact or explicitly unavailable route compatibility across payload assignments."""

    status: PayloadCompatibilityStatus
    total_assignments: int = Field(ge=1)
    compatible_assignments: int | None = Field(default=None, ge=0)
    excluded_assignments: int | None = Field(default=None, ge=0)
    conflict_counts: tuple[FailureReasonCount, ...] = ()
    exhaustive: bool
    warning: str | None = None

    @model_validator(mode="after")
    def validate_accounting(self) -> PayloadCompatibilityAccounting:
        codes = tuple(item.code for item in self.conflict_counts)
        if len(codes) != len(set(codes)):
            raise ValueError("Payload-conflict reason codes must be unique.")
        if self.status is PayloadCompatibilityStatus.COMPLETE:
            if not self.exhaustive:
                raise ValueError("Complete payload accounting must be exhaustive.")
            if self.compatible_assignments is None or self.excluded_assignments is None:
                raise ValueError("Complete payload accounting requires exact assignment counts.")
            if self.compatible_assignments + self.excluded_assignments != self.total_assignments:
                raise ValueError("Payload compatibility counts must equal total assignments.")
            if any(item.count > self.excluded_assignments for item in self.conflict_counts):
                raise ValueError("A payload-conflict count cannot exceed excluded assignments.")
        else:
            if self.exhaustive:
                raise ValueError("Uncomputed payload accounting cannot be exhaustive.")
            if self.compatible_assignments is not None or self.excluded_assignments is not None:
                raise ValueError("Uncomputed payload accounting must not report exact counts.")
            if self.conflict_counts:
                raise ValueError("Uncomputed payload accounting must not report exact conflicts.")
            if not self.warning:
                raise ValueError("Uncomputed payload accounting requires a conservative warning.")
        return self


class NeighborhoodProvenance(HopModel):
    """Replay-relevant implementation and catalog facts for one neighborhood result."""

    hop_version: str
    route_implementation_version: str
    enzyme_catalog_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ProjectionInventoryStatus(StrEnum):
    """Availability of one non-authoritative result projection."""

    AVAILABLE = "available"
    NOT_GENERATED = "not_generated"


class ProjectionInventoryItem(HopModel):
    """Declared renderer projection without output-path authority."""

    projection_schema: str
    renderer_version: str
    status: ProjectionInventoryStatus
    projection_id: str | None = None

    @model_validator(mode="after")
    def validate_availability(self) -> ProjectionInventoryItem:
        if (self.status is ProjectionInventoryStatus.AVAILABLE) != bool(self.projection_id):
            raise ValueError(
                "Available projections require an id; absent projections must omit it."
            )
        return self


class DigitalDesignStatus(StrEnum):
    """Digital authority status exposed by a construction result."""

    VERIFIED = "verified"


class MethodResolutionStatus(StrEnum):
    """Whether any exact local method realization was resolved."""

    RESOLVED = "resolved_under_declared_molecular_model"
    NOT_RESOLVED = "not_resolved"


class ExperimentalEvidenceStatus(StrEnum):
    """Status for experimental evidence outside digital construction discovery."""

    NOT_RECORDED = "not_recorded"


class NeighborhoodClaimBoundary(HopModel):
    """Dimension-specific claims established or explicitly absent from a local result."""

    digital_design: DigitalDesignStatus
    method: MethodResolutionStatus
    physical_construction: ExperimentalEvidenceStatus = ExperimentalEvidenceStatus.NOT_RECORDED
    quality_control: ExperimentalEvidenceStatus = ExperimentalEvidenceStatus.NOT_RECORDED
    biological_activity: ExperimentalEvidenceStatus = ExperimentalEvidenceStatus.NOT_RECORDED


class RealizationGrouping(StrEnum):
    """Supported non-authoritative grouping dimensions."""

    ACHIEVED_GEOMETRY = "achieved_geometry"
    FINAL_PRODUCT = "final_product"


class RealizationGroup(HopModel):
    """One reversible presentation group over exact realization identities."""

    grouping: RealizationGrouping
    group_key: str
    realization_ids: tuple[str, ...] = Field(min_length=1)
    multiplicity: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_multiplicity(self) -> RealizationGroup:
        if self.multiplicity != len(self.realization_ids):
            raise ValueError("Group multiplicity must equal its exact member count.")
        if len(self.realization_ids) != len(set(self.realization_ids)):
            raise ValueError("A realization group must not repeat a member.")
        expected_prefix = {
            RealizationGrouping.ACHIEVED_GEOMETRY: "hop:geometry/",
            RealizationGrouping.FINAL_PRODUCT: "hop:final-product/",
        }[self.grouping]
        if not self.group_key.startswith(expected_prefix):
            raise ValueError("Group key must match the declared grouping dimension.")
        return self


class NeighborhoodDiscoveryResult(HopModel):
    """Exact local realizations with explicit bounded-search completion evidence."""

    schema_id: Literal["hop.neighborhood-discovery-result/v1"] = Field(
        default="hop.neighborhood-discovery-result/v1", alias="schema"
    )
    status: SearchCompletionStatus
    request: LocalNeighborhoodRequest
    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    execution_id: str = Field(pattern=r"^hop:execution/[0-9a-f]{64}@1$")
    shells: tuple[RelaxationShellSummary, ...] = Field(min_length=1)
    realizations: tuple[LocalRealization, ...]
    achieved_geometry_groups: tuple[RealizationGroup, ...]
    rejected_count: int = Field(ge=0)
    failure_reasons: tuple[FailureReasonCount, ...]
    payload_compatibility: PayloadCompatibilityAccounting
    provenance: NeighborhoodProvenance
    projection_inventory: tuple[ProjectionInventoryItem, ...]
    claim_boundary: NeighborhoodClaimBoundary
    truncation_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> NeighborhoodDiscoveryResult:
        if self.problem_id != problem_id(self.request):
            raise ValueError("problem_id must replay from the local request.")
        radii = tuple(shell.radius for shell in self.shells)
        if not radii or radii[0] != 0 or radii != tuple(range(len(radii))):
            raise ValueError("Examined relaxation shells must be contiguous and exact-first.")
        if not all(shell.examined for shell in self.shells):
            raise ValueError("Recorded relaxation shells must have been examined.")
        realization_ids = tuple(item.local_realization_id for item in self.realizations)
        if len(realization_ids) != len(set(realization_ids)):
            raise ValueError("A local result must not repeat an exact realization.")
        shell_ids = tuple(
            realization_id for shell in self.shells for realization_id in shell.realization_ids
        )
        if Counter(shell_ids) != Counter(realization_ids):
            raise ValueError("Relaxation shells must cover every local realization exactly once.")
        shell_by_realization_id = {
            realization_id: shell.radius
            for shell in self.shells
            for realization_id in shell.realization_ids
        }
        for realization in self.realizations:
            actual_radius = self._realization_relaxation_radius(realization)
            if shell_by_realization_id[realization.local_realization_id] != actual_radius:
                raise ValueError(
                    "Each local realization must belong to its declared relaxation shell."
                )
        if self.status is SearchCompletionStatus.TRUNCATED:
            if not self.truncation_reasons:
                raise ValueError("Truncated results require truncation reasons.")
        elif self.truncation_reasons:
            raise ValueError("Only truncated results may contain truncation reasons.")
        if self.status is SearchCompletionStatus.INFEASIBLE and self.realizations:
            raise ValueError("Infeasible results must not contain realizations.")
        if self.status is SearchCompletionStatus.COMPLETE and not self.realizations:
            raise ValueError("A complete local result must contain at least one realization.")
        failure_codes = tuple(item.code for item in self.failure_reasons)
        if len(failure_codes) != len(set(failure_codes)):
            raise ValueError("Failure-reason codes must be unique.")
        if bool(self.rejected_count) != bool(self.failure_reasons):
            raise ValueError("Rejected candidates require failure-reason counts and vice versa.")
        if any(item.count > self.rejected_count for item in self.failure_reasons):
            raise ValueError("A failure-reason count cannot exceed rejected candidates.")
        if self.provenance.enzyme_catalog_digest != self.request.enzyme_catalog_digest:
            raise ValueError("Result provenance must bind the request enzyme-catalog digest.")
        inventory_keys = tuple(
            (item.projection_schema, item.renderer_version) for item in self.projection_inventory
        )
        if len(inventory_keys) != len(set(inventory_keys)):
            raise ValueError("Projection inventory entries must be unique by schema and renderer.")
        grouped_ids = tuple(
            member for group in self.achieved_geometry_groups for member in group.realization_ids
        )
        if any(
            group.grouping is not RealizationGrouping.ACHIEVED_GEOMETRY
            for group in self.achieved_geometry_groups
        ):
            raise ValueError("Neighborhood results may embed only achieved-geometry groups.")
        if Counter(grouped_ids) != Counter(realization_ids) or len(grouped_ids) != len(
            set(grouped_ids)
        ):
            raise ValueError("Achieved-geometry groups must cover every realization exactly once.")
        realizations_by_id = {
            realization.local_realization_id: realization for realization in self.realizations
        }
        for group in self.achieved_geometry_groups:
            member_geometry_ids = {
                geometry_id(realizations_by_id[member].achieved_geometry)
                for member in group.realization_ids
            }
            if member_geometry_ids != {group.group_key}:
                raise ValueError("Achieved-geometry group key must match every member realization.")
        expected_method_status = (
            MethodResolutionStatus.RESOLVED
            if self.realizations
            else MethodResolutionStatus.NOT_RESOLVED
        )
        if self.claim_boundary.method is not expected_method_status:
            raise ValueError("Method claim status must reflect exact local realizations.")
        required_radius = self._required_completion_radius()
        if radii[-1] > required_radius:
            raise ValueError(
                "A result must not record shells beyond the declared relaxation domain."
            )
        if self.status is SearchCompletionStatus.INFEASIBLE and radii[-1] != required_radius:
            raise ValueError("Infeasible results must examine all declared relaxation shells.")
        if (
            self.status is SearchCompletionStatus.COMPLETE
            and self.request.relaxation.mode is RelaxationMode.THROUGH_RADIUS
            and radii[-1] != required_radius
        ):
            raise ValueError("through_radius results must examine all declared relaxation shells.")
        if (
            self.status is SearchCompletionStatus.COMPLETE
            and self.request.relaxation.mode is RelaxationMode.FIRST_FEASIBLE_SHELL
        ):
            hit_shells = tuple(shell.radius for shell in self.shells if shell.realization_ids)
            if hit_shells != (radii[-1],):
                raise ValueError(
                    "first_feasible_shell must stop at the first shell with realizations."
                )
        return self

    def _realization_relaxation_radius(self, realization: LocalRealization) -> int:
        target = self.request.target
        achieved = realization.achieved_geometry
        if type(achieved) is not type(target) or achieved.family != self.request.family.value:
            raise ValueError("A local realization must use the requested neighborhood family.")
        coordinate_names = {coordinate.name for coordinate in self.request.relaxation.coordinates}
        if geometry_fixed_projection(target, coordinate_names) != geometry_fixed_projection(
            achieved, coordinate_names
        ):
            raise ValueError("A local realization changed a non-enabled geometry field.")
        radius = 0
        for coordinate in self.request.relaxation.coordinates:
            achieved_value = geometry_coordinate_value(achieved, coordinate.name)
            if not coordinate.minimum <= achieved_value <= coordinate.maximum:
                raise ValueError("A local realization lies outside the declared relaxation bounds.")
            radius += abs(achieved_value - geometry_coordinate_value(target, coordinate.name))
        if radius > self.request.relaxation.max_radius:
            raise ValueError("A local realization lies outside the declared relaxation radius.")
        return radius

    def _required_completion_radius(self) -> int:
        target = self.request.target
        reachable_radius = sum(
            max(
                abs(geometry_coordinate_value(target, coordinate.name) - coordinate.minimum),
                abs(coordinate.maximum - geometry_coordinate_value(target, coordinate.name)),
            )
            for coordinate in self.request.relaxation.coordinates
        )
        return min(self.request.relaxation.max_radius, reachable_radius)

    @property
    def result_id(self) -> str:
        """Return identity for the ordered result relation and status."""
        return _content_id(
            "neighborhood-result",
            1,
            {
                "schema": self.schema_id,
                "problem_id": self.problem_id,
                "execution_id": self.execution_id,
                "status": self.status,
                "shells": [shell.model_dump(mode="json") for shell in self.shells],
                "realization_ids": [
                    realization.local_realization_id for realization in self.realizations
                ],
                "achieved_geometry_groups": [
                    group.model_dump(mode="json") for group in self.achieved_geometry_groups
                ],
                "rejected_count": self.rejected_count,
                "failure_reasons": [
                    reason.model_dump(mode="json") for reason in self.failure_reasons
                ],
                "payload_compatibility": self.payload_compatibility.model_dump(mode="json"),
                "provenance": self.provenance.model_dump(mode="json"),
                "truncation_reasons": self.truncation_reasons,
            },
        )


class ProjectionReference(HopModel):
    """Non-authoritative grouping projection that preserves exact realization membership."""

    projection_id: str = Field(pattern=r"^hop:projection/[0-9a-f]{64}@1$")
    result_id: str = Field(
        pattern=r"^hop:(?:neighborhood-result|construction-result)/[0-9a-f]{64}@1$"
    )
    projection_schema: str
    renderer_version: str
    realization_ids: tuple[str, ...]
    groups: tuple[RealizationGroup, ...]

    @model_validator(mode="after")
    def validate_projection(self) -> ProjectionReference:
        if len(self.realization_ids) != len(set(self.realization_ids)):
            raise ValueError("Projection realization ids must be unique.")
        grouped_ids = tuple(member for group in self.groups for member in group.realization_ids)
        if Counter(grouped_ids) != Counter(self.realization_ids) or len(grouped_ids) != len(
            set(grouped_ids)
        ):
            raise ValueError("Projection groups must cover every realization exactly once.")
        grouping_dimensions = {group.grouping for group in self.groups}
        if len(grouping_dimensions) > 1:
            raise ValueError("One projection must use one grouping dimension.")
        expected = _content_id(
            "projection",
            1,
            {
                "result_id": self.result_id,
                "projection_schema": self.projection_schema,
                "renderer_version": self.renderer_version,
                "realization_ids": self.realization_ids,
                "groups": [group.model_dump(mode="json") for group in self.groups],
            },
        )
        if self.projection_id != expected:
            raise ValueError("projection_id must replay from the complete projection relation.")
        return self


def grouped_realization_projection(
    *,
    result_id: str,
    projection_schema: str,
    renderer_version: str,
    realization_ids: tuple[str, ...],
    groups: tuple[RealizationGroup, ...],
) -> ProjectionReference:
    """Create a grouping projection only when its groups exactly cover the source relation."""
    grouped_ids = tuple(member for group in groups for member in group.realization_ids)
    if Counter(grouped_ids) != Counter(realization_ids) or len(grouped_ids) != len(
        set(grouped_ids)
    ):
        raise ValueError("Projection groups must cover every realization exactly once.")
    content = {
        "result_id": result_id,
        "projection_schema": projection_schema,
        "renderer_version": renderer_version,
        "realization_ids": realization_ids,
        "groups": [group.model_dump(mode="json") for group in groups],
    }
    return ProjectionReference(
        projection_id=_content_id("projection", 1, content),
        result_id=result_id,
        projection_schema=projection_schema,
        renderer_version=renderer_version,
        realization_ids=realization_ids,
        groups=groups,
    )


__all__ = [
    "BasalPairClass",
    "BasalPairingPosition",
    "BasalTarget",
    "CompleteConstructionRealization",
    "ConstructionConstraints",
    "ConstructionEndpoint",
    "ConstructionExecution",
    "ConstructionPreferences",
    "DigitalDesignStatus",
    "EndGenerationRequest",
    "EnumerationPolicy",
    "ExperimentalEvidenceStatus",
    "FailureReasonCount",
    "FinalPayloadReference",
    "FinalProductReference",
    "FoldbackTarget",
    "LocalGeometryTarget",
    "LocalNeighborhoodFamily",
    "LocalNeighborhoodRequest",
    "LocalRealization",
    "MethodResolutionStatus",
    "NeighborhoodClaimBoundary",
    "NeighborhoodDiscoveryResult",
    "NeighborhoodProvenance",
    "PairState",
    "PairStateException",
    "PayloadCompatibilityAccounting",
    "PayloadCompatibilityStatus",
    "PayloadSourceMap",
    "PayloadSourceSegment",
    "ProjectionInventoryItem",
    "ProjectionInventoryStatus",
    "ProjectionReference",
    "RealizationGroup",
    "RealizationGrouping",
    "RelaxationCoordinate",
    "RelaxationMode",
    "RelaxationPolicy",
    "RelaxationShellSummary",
    "RouteFamily",
    "SearchCompletionStatus",
    "SourceOrientation",
    "geometry_coordinate_value",
    "geometry_fixed_projection",
    "geometry_id",
    "geometry_with_coordinate_value",
    "grouped_realization_projection",
    "problem_id",
    "validate_linear_source_map",
    "validate_linear_source_payload",
]
