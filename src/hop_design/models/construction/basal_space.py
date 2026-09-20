"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal_space.py

Defines complete canonical basal populations with full-source molecular support.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import EnzymeProvisioningPolicy
from hop_design.models.physical import SiteOrientation, Strand
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import normalize_dna_sequence

from .payload import (
    ConstructionEndpoint,
    FinalPayloadReference,
    RouteFamily,
    _content_id,
    validate_linear_source_payload,
)
from .search import BasalGeometryDomain
from .sequence_sets import SequenceSet, SequenceSpaceLimits
from .targets import BasalPairAllowance, BasalTarget


class BasalSequenceRequest(HopModel):
    """Exhaustive canonical local admission within one finite basal geometry domain."""

    schema_id: Literal["hop.basal-sequence-request/v1"] = Field(
        default="hop.basal-sequence-request/v1", alias="schema"
    )
    payload: FinalPayloadReference
    route_family: RouteFamily
    endpoint: ConstructionEndpoint
    geometry_domain: BasalGeometryDomain
    enzyme_provisioning: EnzymeProvisioningPolicy
    max_retained_overhead_nt: int = Field(ge=0, le=256)
    limits: SequenceSpaceLimits

    @model_validator(mode="after")
    def validate_scope(self) -> BasalSequenceRequest:
        validate_linear_source_payload(self.payload)
        if self.endpoint not in {
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            ConstructionEndpoint.CLONE_READY_DUPLEX,
        }:
            raise ValueError("Basal sequence populations require a PCR-bearing endpoint.")
        geometry = self.geometry_domain
        if any(
            c.allowed_class is not BasalPairAllowance.MATCH for c in geometry.pairing_constraints
        ):
            raise ValueError("Compact basal populations require canonical pairing permissions.")
        release = geometry.future_release
        if (self.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX) != (release is not None):
            raise ValueError("Basal endpoint and future-release requirement disagree.")
        if release is not None and any(
            nick + len(geometry.pairing_constraints)
            < release.payload_end_offset_bp + len(release.cohesive_end_sequence)
            for nick in geometry.nick_offsets_nt
        ):
            raise ValueError("The basal local sequence window must cover its future end footprint.")
        return self


class BasalProgramSupport(HopModel):
    """One exact end and enzyme program with admitted full-source and local words."""

    target: BasalTarget
    nick_enzyme_id: ReferenceId
    nick_orientation: SiteOrientation
    future_release_enzyme_id: ReferenceId | None
    placement_failure: str | None
    placement_count: int = Field(ge=0)
    source_window_start: int | None = Field(ge=0)
    source_sequences: SequenceSet | None
    sequences: SequenceSet

    @model_validator(mode="after")
    def validate_support(self) -> BasalProgramSupport:
        if self.placement_failure is not None:
            if (
                self.placement_count
                or self.source_sequences is not None
                or self.source_window_start is not None
                or self.sequences.cardinality
            ):
                raise ValueError("Excluded basal placement cannot contain sequence support.")
        elif self.source_sequences is None or self.source_window_start is None:
            raise ValueError("A solved basal placement requires full-source sequence support.")
        else:
            if (
                not self.sequences.cardinality
                <= self.source_sequences.cardinality
                <= self.placement_count
            ):
                raise ValueError(
                    "Basal local admission must be supported by admitted source words."
                )
            if (
                self.source_window_start + self.sequences.length_nt
                > self.source_sequences.length_nt
            ):
                raise ValueError("Basal local window exceeds its supporting source.")
        return self


def basal_case_id(
    payload_sequence: str, endpoint: ConstructionEndpoint, geometry: BasalGeometryDomain
) -> str:
    """Identify a local population independently of budget and enzyme witnesses."""
    return _content_id(
        "basal-sequence-case",
        1,
        {
            "payload_sequence": payload_sequence,
            "endpoint": endpoint.value,
            "geometry": geometry.model_dump(mode="json"),
        },
    )


class BasalSequenceCase(HopModel):
    """One exact payload, nick coordinate and strand, pooling exact-end programs."""

    case_id: str = Field(pattern=r"^hop:basal-sequence-case/[0-9a-f]{64}@1$")
    payload_sequence: str
    endpoint: ConstructionEndpoint
    geometry: BasalGeometryDomain
    candidate_count: int = Field(ge=1)
    programs: tuple[BasalProgramSupport, ...] = Field(max_length=100_000)
    sequences: SequenceSet

    @model_validator(mode="after")
    def validate_population(self) -> BasalSequenceCase:
        if self.case_id != basal_case_id(self.payload_sequence, self.endpoint, self.geometry):
            raise ValueError("Basal case identity disagrees with its molecular population.")
        if (
            normalize_dna_sequence(self.payload_sequence, allow_degenerate=False)
            != self.payload_sequence
        ):
            raise ValueError("Basal case payload must be canonical exact DNA.")
        if len(self.geometry.nick_offsets_nt) != 1 or not isinstance(
            self.geometry.nick_strand, Strand
        ):
            raise ValueError("Basal case requires one exact nick coordinate and strand.")
        width = self.geometry.nick_offsets_nt[0] + len(self.geometry.pairing_constraints)
        if self.candidate_count != 4**width:
            raise ValueError("Basal raw population must contain every local source assignment.")
        if any(
            s.length_nt != width for s in (self.sequences, *(p.sequences for p in self.programs))
        ):
            raise ValueError("Basal local sequence lengths disagree with the geometry.")
        return self


class BasalSequenceResult(HopModel):
    """Complete local membership with recoverable source support, not complete materials."""

    schema_id: Literal["hop.basal-sequence-result/v1"] = Field(
        default="hop.basal-sequence-result/v1", alias="schema"
    )
    request: BasalSequenceRequest
    hop_version: str
    route_implementation_version: str
    admission_implementation_version: Literal["basal-sequence-space/1"] = "basal-sequence-space/1"
    completion: Literal["complete"] = "complete"
    claim_scope: Literal["local_molecular_admission"] = "local_molecular_admission"
    cases: tuple[BasalSequenceCase, ...] = Field(max_length=100_000)
    candidate_count: int = Field(ge=0)
    admitted_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_totals(self) -> BasalSequenceResult:
        if self.candidate_count != sum(
            c.candidate_count for c in self.cases
        ) or self.admitted_count != sum(c.sequences.cardinality for c in self.cases):
            raise ValueError("Basal population totals disagree with their exact cases.")
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("Basal population cases must be unique.")
        limits = self.request.limits
        if (
            len(self.cases) > limits.max_cases
            or sum(len(c.programs) for c in self.cases) > limits.max_programs
        ):
            raise ValueError("Basal result exceeds its case or program budget.")
        decisions = sum(
            len(case.sequences.decisions)
            + sum(
                len(p.sequences.decisions)
                + (len(p.source_sequences.decisions) if p.source_sequences is not None else 0)
                for p in case.programs
            )
            for case in self.cases
        )
        if decisions > limits.max_result_decisions:
            raise ValueError("Basal result exceeds its serialized decision budget.")
        return self

    @property
    def result_id(self) -> str:
        """Bind request, implementation, complete coverage, and exact supporting sets."""
        return _content_id("basal-sequence-result", 1, self)
