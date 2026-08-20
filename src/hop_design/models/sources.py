"""Typed payload-record, collection, and expansion contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.payload import ExactPayload, Payload


class DuplicateSequencePolicy(StrEnum):
    """An explicit disposition for records that carry the same sequence."""

    FAIL = "fail"
    DEDUPE = "dedupe"
    KEEP = "keep"


class PayloadRecord(HopModel):
    """One caller-identified exact or symbolic payload."""

    record_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    payload: Payload


class PayloadSourceLimits(HopModel):
    """Resource bounds applied before and during eager local file ingestion."""

    max_bytes: int = Field(ge=1)
    max_records: int = Field(ge=1)
    max_total_nt: int = Field(ge=1)


class PayloadCollection(HopModel):
    """A normalized collection with its duplicate-sequence decision recorded."""

    records: tuple[PayloadRecord, ...] = Field(min_length=1)
    duplicate_sequence_policy: DuplicateSequencePolicy


class PayloadExpansionResult(HopModel):
    """One explicitly expanded record and its precomputed cardinality."""

    source_record_id: str
    cardinality: int = Field(ge=1)
    records: tuple[PayloadRecord, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_expansion(self) -> PayloadExpansionResult:
        if len(self.records) != self.cardinality:
            raise ValueError("Expanded record count must equal the declared cardinality.")
        if any(not isinstance(record.payload, ExactPayload) for record in self.records):
            raise ValueError("Expanded payload records must all be exact.")
        return self

    @property
    def exact_payloads(self) -> tuple[ExactPayload, ...]:
        """Return exact variants after model validation has established their type."""
        payloads: list[ExactPayload] = []
        for record in self.records:
            if not isinstance(record.payload, ExactPayload):
                raise ValueError("Expanded payload records must all be exact.")
            payloads.append(record.payload)
        return tuple(payloads)


__all__ = [
    "DuplicateSequencePolicy",
    "PayloadCollection",
    "PayloadExpansionResult",
    "PayloadRecord",
    "PayloadSourceLimits",
]
