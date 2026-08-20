from __future__ import annotations

from pathlib import Path

import pytest

from hop_design.design.payloads import (
    DuplicatePayloadError,
    PayloadSourceLimitError,
    VariantBudgetExceededError,
    collect_payloads,
    expand_payload,
    load_csv_payloads,
    load_fasta_payloads,
)
from hop_design.models.payload import DegeneratePayload, ExactPayload
from hop_design.models.sources import (
    DuplicateSequencePolicy,
    PayloadRecord,
    PayloadSourceLimits,
)


def test_explicit_degenerate_expansion_is_deterministic_and_budgeted() -> None:
    result = expand_payload(
        PayloadRecord(record_id="symbolic-01", payload=DegeneratePayload(sequence="RY")),
        max_variants=4,
    )

    assert result.cardinality == 4
    assert [record.record_id for record in result.records] == [
        "symbolic-01-v0001",
        "symbolic-01-v0002",
        "symbolic-01-v0003",
        "symbolic-01-v0004",
    ]
    assert [record.payload.sequence for record in result.records] == ["AC", "AT", "GC", "GT"]
    assert all(isinstance(record.payload, ExactPayload) for record in result.records)


def test_expansion_calculates_cardinality_before_enforcing_budget() -> None:
    with pytest.raises(VariantBudgetExceededError) as captured:
        expand_payload(
            PayloadRecord(record_id="symbolic-02", payload=DegeneratePayload(sequence="BDN")),
            max_variants=35,
        )

    assert captured.value.cardinality == 36
    assert captured.value.max_variants == 35


def test_payload_collection_requires_explicit_duplicate_sequence_policy() -> None:
    records = (
        PayloadRecord(record_id="first", payload=ExactPayload(sequence="ACGT")),
        PayloadRecord(record_id="second", payload=ExactPayload(sequence="ACGT")),
    )

    with pytest.raises(DuplicatePayloadError, match="ACGT"):
        collect_payloads(records, duplicate_policy=DuplicateSequencePolicy.FAIL)

    deduped = collect_payloads(records, duplicate_policy=DuplicateSequencePolicy.DEDUPE)
    kept = collect_payloads(records, duplicate_policy=DuplicateSequencePolicy.KEEP)
    assert [record.record_id for record in deduped.records] == ["first"]
    assert [record.record_id for record in kept.records] == ["first", "second"]


def test_fasta_and_csv_sources_feed_the_same_typed_payload_records(tmp_path: Path) -> None:
    fasta = tmp_path / "payloads.fasta"
    csv = tmp_path / "payloads.csv"
    fasta.write_text(">exact\nACGT\n>symbolic\nNN\n", encoding="utf-8")
    csv.write_text("record_id,sequence\nexact,ACGT\nsymbolic,NN\n", encoding="utf-8")

    fasta_records = load_fasta_payloads(fasta)
    csv_records = load_csv_payloads(csv, id_column="record_id", sequence_column="sequence")

    assert fasta_records == csv_records
    assert isinstance(fasta_records[0].payload, ExactPayload)
    assert isinstance(fasta_records[1].payload, DegeneratePayload)


def test_fasta_and_csv_fail_fast_on_ambiguous_or_malformed_rows(tmp_path: Path) -> None:
    duplicate_fasta = tmp_path / "duplicate.fasta"
    missing_csv_column = tmp_path / "missing.csv"
    duplicate_fasta.write_text(">same\nACGT\n>same\nTGCA\n", encoding="utf-8")
    missing_csv_column.write_text("name,dna\none,ACGT\n", encoding="utf-8")

    with pytest.raises(DuplicatePayloadError, match="record id"):
        load_fasta_payloads(duplicate_fasta)
    with pytest.raises(ValueError, match="required columns"):
        load_csv_payloads(
            missing_csv_column,
            id_column="record_id",
            sequence_column="sequence",
        )


def test_file_payload_sources_enforce_byte_record_and_total_nt_limits(tmp_path: Path) -> None:
    fasta_path = tmp_path / "payloads.fasta"
    fasta_path.write_text(">a\nACGT\n>b\nNNNN\n", encoding="utf-8")

    with pytest.raises(PayloadSourceLimitError) as byte_error:
        load_fasta_payloads(
            fasta_path,
            limits=PayloadSourceLimits(max_bytes=1, max_records=10, max_total_nt=100),
        )
    assert byte_error.value.limit_name == "max_bytes"

    with pytest.raises(PayloadSourceLimitError) as record_error:
        load_fasta_payloads(
            fasta_path,
            limits=PayloadSourceLimits(max_bytes=100, max_records=1, max_total_nt=100),
        )
    assert record_error.value.actual == 2

    with pytest.raises(PayloadSourceLimitError) as nt_error:
        load_fasta_payloads(
            fasta_path,
            limits=PayloadSourceLimits(max_bytes=100, max_records=10, max_total_nt=7),
        )
    assert nt_error.value.limit_name == "max_total_nt"
    assert nt_error.value.actual == 8


def test_file_payload_sources_reject_symlinks(tmp_path: Path) -> None:
    source = tmp_path / "payloads.fasta"
    source.write_text(">a\nACGT\n", encoding="utf-8")
    linked = tmp_path / "linked.fasta"
    linked.symlink_to(source)

    with pytest.raises(ValueError, match="symlink"):
        load_fasta_payloads(linked)
