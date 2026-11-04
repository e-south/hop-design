"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_foldback_sequence_space_public.py

Exercises portable foldback set verification and exact molecular member recovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json

import pytest

from hop_design import construction
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.construction.foldback_space import FoldbackSequenceResult
from hop_design.serialization import canonical_json_bytes
from tests.contract.test_foldback_population_discovery import _space_request


def _discover(tmp_path):
    source = tmp_path / "request.json"
    source.write_bytes(canonical_json_bytes(_space_request()))
    return construction.discover_foldback_sequence_space(source)


def test_portable_result_replays_every_case_and_recovers_an_exact_member(tmp_path):
    receipt = _discover(tmp_path)
    result = FoldbackSequenceResult.model_validate_json(receipt.json_bytes)
    assert json.loads(receipt.json_bytes)["cases"][0]["case_id"] == result.cases[0].case_id
    assert receipt.admitted_count == 72
    assert receipt.candidate_count == 8192
    assert receipt.result_id == result.result_id
    output = receipt.write(tmp_path / "result")
    loaded = construction.load_verified_foldback_sequence_space(output / "result.json")
    assert loaded.json_bytes == receipt.json_bytes
    for case in result.cases:
        for rank in (0, 18, 35):
            member = json.loads(
                loaded.member_json(case_id=case.case_id, rank=rank, program_index=0)
            )
            realization = FoldbackLocalRealization.model_validate_json(
                json.dumps(member["realization"])
            )
            assert member["result_id"] == receipt.result_id
            assert member["independent_sequence"] == case.sequences.member_at(rank)
            assert realization.local_realization.achieved_geometry == case.target
            assert realization.payload_sequence == case.payload_sequence
            assert realization.retained_overhead.retained_overhead_nt == 9
    with pytest.raises(FileExistsError):
        receipt.write(output)


def test_portable_loader_rejects_reconciled_false_membership(tmp_path):
    result = json.loads(_discover(tmp_path).json_bytes)
    case = result["cases"][0]
    case["sequences"].update(root=0, decisions=[], cardinality=0)
    result["admitted_count"] = 36
    path = tmp_path / "forged.json"
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="deterministic discovery replay"):
        construction.load_verified_foldback_sequence_space(path)


@pytest.mark.parametrize(
    "schema", ("hop.foldback-sequence-request/v0", "hop.local-neighborhood-request/v7")
)
def test_request_rejects_unknown_schema(tmp_path, schema):
    source = json.loads(canonical_json_bytes(_space_request()))
    source["schema"] = schema
    path = tmp_path / "request.json"
    path.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="Unsupported"):
        construction.discover_foldback_sequence_space(path)


def test_source_readers_reject_symlinks_and_duplicate_keys(tmp_path):
    receipt = _discover(tmp_path)
    path = tmp_path / "result.json"
    path.write_bytes(receipt.json_bytes)
    link = tmp_path / "link.json"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="symlink"):
        construction.load_verified_foldback_sequence_space(link)
    path.write_text('{"schema":"hop.foldback-sequence-result/v1","schema":"other"}')
    with pytest.raises(ValueError, match="duplicate"):
        construction.load_verified_foldback_sequence_space(path)


@pytest.mark.parametrize(
    "selection",
    (
        {"case_id": "absent"},
        {"rank": -1},
        {"program_index": -1},
        {"rank": True},
        {"program_index": True},
    ),
)
def test_member_recovery_rejects_invalid_selection(tmp_path, selection):
    receipt = _discover(tmp_path)
    result = FoldbackSequenceResult.model_validate_json(receipt.json_bytes)
    arguments = {"case_id": result.cases[0].case_id, "rank": 0, "program_index": 0} | selection
    with pytest.raises((ValueError, IndexError)):
        receipt.member_json(**arguments)


@pytest.mark.parametrize("source", (True, False))
def test_file_readers_enforce_byte_limits_before_decoding(tmp_path, source):
    path = tmp_path / "oversized.json"
    limit = 1_000_000 if source else 64 * 1024 * 1024
    with path.open("wb") as handle:
        handle.truncate(limit + 1)
    operation = (
        construction.discover_foldback_sequence_space
        if source
        else construction.load_verified_foldback_sequence_space
    )
    with pytest.raises(ValueError, match="max_bytes exceeded"):
        operation(path)


def test_result_reader_rejects_unknown_schema(tmp_path):
    path = tmp_path / "unknown.json"
    path.write_text('{"schema":"hop.foldback-sequence-result/v0"}')
    with pytest.raises(ValueError, match="Unsupported"):
        construction.load_verified_foldback_sequence_space(path)
