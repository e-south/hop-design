"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/payload.py

Defines payload-centered construction contracts and discovery evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from itertools import pairwise
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.payload import Payload
from hop_design.models.sequence import (
    iupac_bases,
    normalize_dna_sequence,
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
    *,
    allowed_orientations: tuple[SourceOrientation, ...] = (SourceOrientation.FORWARD,),
) -> None:
    """Require the current route's one contiguous payload encoding."""
    if len(source_map.segments) != 1:
        raise ValueError("linear_source/v1 requires one contiguous source segment.")
    segment = source_map.segments[0]
    expected = Span(start=payload.basal_boundary, end=payload.foldback_boundary)
    if segment.payload_span != expected:
        raise ValueError("The linear source segment must cover the complete final payload.")
    if segment.orientation not in allowed_orientations:
        raise ValueError("linear_source/v1 requires a forward payload source segment.")
