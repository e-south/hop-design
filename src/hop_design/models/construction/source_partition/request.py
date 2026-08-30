"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source_partition/request.py

Defines exact source-duplex, survivor, and bounded partition-search requests.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from itertools import pairwise
from math import comb
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import (
    FinalPayloadReference,
    PayloadSourceMap,
    SourceOrientation,
    validate_linear_source_map,
    validate_linear_source_payload,
)
from hop_design.models.coordinates import Span
from hop_design.models.enzymes import (
    EnzymeClass,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    characterized_enzyme_catalog_digest,
)
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry, FragmentLengthSelection
from hop_design.models.sequence import (
    SequenceValidationError,
    iupac_bases,
    normalize_dna_sequence,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest


def _content_id(kind: str, value: object) -> str:
    digest = sha256_digest(canonical_json_bytes(value)).removeprefix("sha256:")
    return f"hop:{kind}/{digest}@1"


def _canonical_provisioning_policy(
    policy: EnzymeProvisioningPolicy,
) -> dict[str, object]:
    """Return order-independent authored provisioning policy content."""
    return {
        "enzyme_catalog_digest": characterized_enzyme_catalog_digest(policy.catalog),
        "allowed_enzyme_ids": tuple(sorted(policy.allowed_enzyme_ids)),
        "forbidden_enzyme_ids": tuple(sorted(policy.forbidden_enzyme_ids)),
        "reserved_enzyme_ids": tuple(sorted(policy.reserved_enzyme_ids)),
        "max_operations": policy.max_operations,
        "role_restrictions": tuple(
            {
                "role": restriction.role,
                "allowed_enzyme_ids": tuple(sorted(restriction.allowed_enzyme_ids)),
            }
            for restriction in sorted(
                policy.role_restrictions,
                key=lambda item: item.role.value,
            )
        ),
    }


class SourceDuplexMaterial(HopModel):
    """One exact duplex precursor expressed by its top strand and terminal chemistry."""

    material_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    top_sequence_5prime: str
    top_five_prime_end: EndChemistry
    top_three_prime_end: EndChemistry
    bottom_five_prime_end: EndChemistry
    bottom_three_prime_end: EndChemistry

    @field_validator("top_sequence_5prime", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("Source-duplex sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)


class SourcePartitionSurvivor(HopModel):
    """One exact strand fragment that must survive the declared length selection."""

    survivor_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,63}$")
    precursor_strand: Strand
    source_span: Span

    @model_validator(mode="after")
    def validate_nonempty(self) -> SourcePartitionSurvivor:
        if self.source_span.length.value == 0:
            raise ValueError("A required source-partition survivor must not be empty.")
        return self


class SourcePartitionConstraints(HopModel):
    """Exact size-selection outcome and finite enzyme-program width."""

    selection: FragmentLengthSelection
    required_survivors: tuple[SourcePartitionSurvivor, ...] = Field(min_length=1)
    max_enzymes_per_program: int = Field(ge=1)

    @field_validator("required_survivors", mode="after")
    @classmethod
    def canonicalize_survivors(
        cls, values: tuple[SourcePartitionSurvivor, ...]
    ) -> tuple[SourcePartitionSurvivor, ...]:
        return tuple(
            sorted(
                values,
                key=lambda item: (
                    item.precursor_strand.value,
                    item.source_span.start.offset,
                    item.source_span.end.offset,
                    item.survivor_id,
                ),
            )
        )

    @model_validator(mode="after")
    def validate_survivors(self) -> SourcePartitionConstraints:
        survivor_ids = tuple(item.survivor_id for item in self.required_survivors)
        if len(survivor_ids) != len(set(survivor_ids)):
            raise ValueError("Required source-partition survivor ids must be unique.")
        for strand in Strand:
            spans = tuple(
                item.source_span
                for item in self.required_survivors
                if item.precursor_strand is strand
            )
            for left, right in pairwise(spans):
                if left.end.offset > right.start.offset:
                    raise ValueError("Required survivor spans must not overlap on one strand.")
        return self


class SourcePartitionEnumerationPolicy(HopModel):
    """Execution-only bounds for canonical enzyme-subset enumeration."""

    max_search_nodes: int = Field(ge=1)
    max_realizations: int = Field(ge=1)


class SourcePartitionDiscoveryRequest(HopModel):
    """One exact source, payload relation, enzyme domain, and required partition."""

    schema_id: Literal["hop.source-partition-request/v1"] = Field(
        default="hop.source-partition-request/v1", alias="schema"
    )
    payload: FinalPayloadReference
    source: SourceDuplexMaterial
    payload_source_map: PayloadSourceMap
    enzyme_provisioning: EnzymeProvisioningPolicy
    constraints: SourcePartitionConstraints
    enumeration: SourcePartitionEnumerationPolicy

    @model_validator(mode="after")
    def validate_request(self) -> SourcePartitionDiscoveryRequest:
        validate_linear_source_payload(self.payload)
        validate_linear_source_map(self.payload, self.payload_source_map)
        sequence_nt = len(self.source.top_sequence_5prime)
        segment = self.payload_source_map.segments[0]
        if segment.source_material_id != self.source.material_id:
            raise ValueError("Payload source mapping must reference the supplied source duplex.")
        if segment.source_span.end.offset > sequence_nt:
            raise ValueError("Payload source mapping must stay inside the supplied source duplex.")
        source_payload = self.source.top_sequence_5prime[
            segment.source_span.start.offset : segment.source_span.end.offset
        ]
        authored_payload = self.payload.payload.sequence
        if segment.orientation is not SourceOrientation.FORWARD or any(
            base not in iupac_bases(symbol)
            for base, symbol in zip(source_payload, authored_payload, strict=True)
        ):
            raise ValueError("Payload source mapping must encode a member of the authored payload.")
        if any(
            survivor.source_span.end.offset > sequence_nt
            for survivor in self.constraints.required_survivors
        ):
            raise ValueError("Required survivor spans must stay inside the source duplex.")
        if not any(
            survivor.precursor_strand is Strand.TOP
            and survivor.source_span.start.offset <= segment.source_span.start.offset
            and survivor.source_span.end.offset >= segment.source_span.end.offset
            for survivor in self.constraints.required_survivors
        ):
            raise ValueError(
                "The mapped payload source span must be retained by a top-strand survivor."
            )
        candidate_ids = self.candidate_enzyme_ids
        if not candidate_ids:
            raise ValueError("Source-partition discovery requires a provisioned nickase.")
        if self.constraints.max_enzymes_per_program > len(candidate_ids):
            raise ValueError(
                "max_enzymes_per_program must not exceed the provisioned nickase count."
            )
        return self

    @property
    def candidate_enzyme_ids(self) -> tuple[str, ...]:
        """Return the canonical provisioned nickase domain for strand exposure."""
        return tuple(
            sorted(
                enzyme.enzyme_id
                for enzyme in self.enzyme_provisioning.catalog.enzymes
                if enzyme.enzyme_class is EnzymeClass.NICKASE
                and self.enzyme_provisioning.permits(
                    enzyme.enzyme_id,
                    role=EnzymeRole.STRAND_EXPOSURE,
                )
            )
        )

    @property
    def candidate_space_size(self) -> int:
        """Return the number of nonempty enzyme subsets inside the declared width."""
        count = len(self.candidate_enzyme_ids)
        return sum(
            comb(count, width) for width in range(1, self.constraints.max_enzymes_per_program + 1)
        )

    @property
    def problem_id(self) -> str:
        """Return scientific identity excluding labels, vendor metadata, and search limits."""
        policy = self.enzyme_provisioning
        seed = {
            "payload_spec_id": self.payload.payload_spec_id,
            "source": self.source.model_dump(mode="json"),
            "payload_source_map": self.payload_source_map.model_dump(mode="json"),
            "enzyme_catalog_digest": characterized_enzyme_catalog_digest(policy.catalog),
            "enzyme_policy": {
                "candidate_enzyme_ids": self.candidate_enzyme_ids,
                "max_operations": policy.max_operations,
            },
            "constraints": self.constraints.model_dump(mode="json"),
        }
        return _content_id("source-partition-problem", seed)

    @property
    def request_id(self) -> str:
        """Return execution identity including the finite enumeration policy."""
        return _content_id(
            "source-partition-request",
            {
                "problem_id": self.problem_id,
                "enzyme_provisioning": _canonical_provisioning_policy(self.enzyme_provisioning),
                "enumeration": self.enumeration.model_dump(mode="json"),
            },
        )


__all__ = [
    "SourceDuplexMaterial",
    "SourcePartitionConstraints",
    "SourcePartitionDiscoveryRequest",
    "SourcePartitionEnumerationPolicy",
    "SourcePartitionSurvivor",
]
