"""Ergonomic iterable, FASTA, CSV, and explicit expansion operations."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from itertools import product
from math import prod
from pathlib import Path

from hop_design.models.payload import DegeneratePayload, ExactPayload, Payload
from hop_design.models.sequence import EXACT_DNA_ALPHABET, iupac_bases, normalize_dna_sequence
from hop_design.models.sources import (
    DuplicateSequencePolicy,
    PayloadCollection,
    PayloadExpansionResult,
    PayloadRecord,
    PayloadSourceLimits,
)


class DuplicatePayloadError(ValueError):
    """Raised when record identity or sequence duplication violates declared policy."""


class VariantBudgetExceededError(ValueError):
    """Raised before allocation when symbolic expansion exceeds its hard budget."""

    def __init__(self, *, cardinality: int, max_variants: int) -> None:
        self.cardinality = cardinality
        self.max_variants = max_variants
        super().__init__(
            f"Payload expansion cardinality {cardinality} exceeds max_variants {max_variants}."
        )


class PayloadSourceLimitError(ValueError):
    """Raised when an eager file source exceeds one declared resource bound."""

    def __init__(self, *, limit_name: str, actual: int, limit: int) -> None:
        self.limit_name = limit_name
        self.actual = actual
        self.limit = limit
        super().__init__(f"Payload source {limit_name} exceeded: {actual} > {limit}.")


DEFAULT_PAYLOAD_SOURCE_LIMITS = PayloadSourceLimits(
    max_bytes=10_000_000,
    max_records=100_000,
    max_total_nt=10_000_000,
)


def _validate_source_path(source: Path, *, limits: PayloadSourceLimits) -> None:
    if source.is_symlink():
        raise ValueError("Payload source must not be a symlink.")
    if not source.is_file():
        raise ValueError(f"Payload source is not a regular file: {source}.")
    size_bytes = source.stat().st_size
    if size_bytes > limits.max_bytes:
        raise PayloadSourceLimitError(
            limit_name="max_bytes",
            actual=size_bytes,
            limit=limits.max_bytes,
        )


def _enforce_collection_limits(
    records: list[PayloadRecord],
    *,
    total_nt: int,
    limits: PayloadSourceLimits,
) -> None:
    if len(records) > limits.max_records:
        raise PayloadSourceLimitError(
            limit_name="max_records",
            actual=len(records),
            limit=limits.max_records,
        )
    if total_nt > limits.max_total_nt:
        raise PayloadSourceLimitError(
            limit_name="max_total_nt",
            actual=total_nt,
            limit=limits.max_total_nt,
        )


def _payload(sequence: str) -> Payload:
    normalized = normalize_dna_sequence(sequence, allow_degenerate=True)
    if set(normalized) <= EXACT_DNA_ALPHABET:
        return ExactPayload(sequence=normalized)
    return DegeneratePayload(sequence=normalized)


def collect_payloads(
    records: Iterable[PayloadRecord],
    *,
    duplicate_policy: DuplicateSequencePolicy,
) -> PayloadCollection:
    """Normalize an iterable under explicit record-id and sequence duplicate contracts."""
    collected: list[PayloadRecord] = []
    record_ids: set[str] = set()
    seen_sequences: set[str] = set()
    for record in records:
        if record.record_id in record_ids:
            raise DuplicatePayloadError(f"Duplicate payload record id: {record.record_id!r}.")
        record_ids.add(record.record_id)
        sequence = record.payload.sequence
        if sequence in seen_sequences:
            if duplicate_policy is DuplicateSequencePolicy.FAIL:
                raise DuplicatePayloadError(f"Duplicate payload sequence: {sequence}.")
            if duplicate_policy is DuplicateSequencePolicy.DEDUPE:
                continue
        seen_sequences.add(sequence)
        collected.append(record)
    if not collected:
        raise ValueError("Payload collection must contain at least one record.")
    return PayloadCollection(
        records=tuple(collected),
        duplicate_sequence_policy=duplicate_policy,
    )


def expand_payload(record: PayloadRecord, *, max_variants: int) -> PayloadExpansionResult:
    """Expand one symbolic payload only after checking its exact variant count."""
    if max_variants < 1:
        raise ValueError("max_variants must be at least 1.")
    base_choices = tuple(tuple(sorted(iupac_bases(symbol))) for symbol in record.payload.sequence)
    cardinality = prod(len(choices) for choices in base_choices)
    if cardinality > max_variants:
        raise VariantBudgetExceededError(
            cardinality=cardinality,
            max_variants=max_variants,
        )
    records: tuple[PayloadRecord, ...]
    if isinstance(record.payload, ExactPayload):
        records = (record,)
    else:
        width = max(4, len(str(cardinality)))
        records = tuple(
            PayloadRecord(
                record_id=f"{record.record_id}-v{index:0{width}d}",
                payload=ExactPayload(sequence="".join(bases)),
            )
            for index, bases in enumerate(product(*base_choices), start=1)
        )
    return PayloadExpansionResult(
        source_record_id=record.record_id,
        cardinality=cardinality,
        records=records,
    )


def load_fasta_payloads(
    path: str | Path,
    *,
    limits: PayloadSourceLimits = DEFAULT_PAYLOAD_SOURCE_LIMITS,
) -> tuple[PayloadRecord, ...]:
    """Load a small FASTA source into the same typed records used by inline callers."""
    source = Path(path)
    _validate_source_path(source, limits=limits)
    records: list[PayloadRecord] = []
    current_id: str | None = None
    sequence_lines: list[str] = []
    total_nt = 0

    def finish_record() -> None:
        nonlocal total_nt
        if current_id is None:
            return
        record = PayloadRecord(record_id=current_id, payload=_payload("".join(sequence_lines)))
        records.append(record)
        total_nt += len(record.payload.sequence)
        _enforce_collection_limits(records, total_nt=total_nt, limits=limits)

    for line_number, raw_line in enumerate(
        source.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            finish_record()
            current_id = line[1:].strip().split(maxsplit=1)[0]
            if not current_id:
                raise ValueError(f"FASTA header on line {line_number} is empty.")
            sequence_lines = []
        else:
            if current_id is None:
                raise ValueError("FASTA sequence data must follow a header.")
            sequence_lines.append(line)
    finish_record()
    collection = collect_payloads(records, duplicate_policy=DuplicateSequencePolicy.KEEP)
    return collection.records


def load_csv_payloads(
    path: str | Path,
    *,
    id_column: str,
    sequence_column: str,
    limits: PayloadSourceLimits = DEFAULT_PAYLOAD_SOURCE_LIMITS,
) -> tuple[PayloadRecord, ...]:
    """Load explicit CSV columns into typed payload records."""
    source = Path(path)
    _validate_source_path(source, limits=limits)
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or ())
        required = {id_column, sequence_column}
        if not required <= fieldnames:
            missing = ", ".join(sorted(required - fieldnames))
            raise ValueError(f"CSV is missing required columns: {missing}.")
        records: list[PayloadRecord] = []
        total_nt = 0
        for row in reader:
            record = PayloadRecord(
                record_id=row[id_column].strip(),
                payload=_payload(row[sequence_column]),
            )
            records.append(record)
            total_nt += len(record.payload.sequence)
            _enforce_collection_limits(records, total_nt=total_nt, limits=limits)
    collection = collect_payloads(records, duplicate_policy=DuplicateSequencePolicy.KEEP)
    return collection.records


__all__ = [
    "DEFAULT_PAYLOAD_SOURCE_LIMITS",
    "DuplicatePayloadError",
    "PayloadSourceLimitError",
    "VariantBudgetExceededError",
    "collect_payloads",
    "expand_payload",
    "load_csv_payloads",
    "load_fasta_payloads",
]
