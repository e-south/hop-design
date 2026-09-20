"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_basal_sequence_space_public.py

Checks portable basal population results and exact molecular member recovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json

import pytest

from hop_design.design.construction.basal import discover_basal_neighborhood
from tests.contract.test_basal_sequence_space import canonical_request, compact_request


def test_public_basal_population_round_trip_and_exact_molecular_recovery(tmp_path):
    from hop_design.construction import (
        discover_basal_sequence_space,
        load_verified_basal_sequence_space,
    )

    local = canonical_request()
    request = compact_request(local)
    source = tmp_path / "request.json"
    source.write_text(request.model_dump_json(by_alias=True))
    receipt = discover_basal_sequence_space(source)
    result_path = receipt.write(tmp_path / "result") / "result.json"
    loaded = load_verified_basal_sequence_space(result_path)
    assert loaded.result_id == receipt.result_id
    assert loaded.json_bytes == receipt.json_bytes
    assert loaded.candidate_count == 256
    assert loaded.admitted_count == 16
    case = json.loads(loaded.json_bytes)["cases"][0]
    expected = {
        record.basal_realization_id for record in discover_basal_neighborhood(local).realizations
    }
    actual = set()
    for rank in range(16):
        member = json.loads(loaded.member_json(case_id=case["case_id"], rank=rank, program_index=0))
        assert member["result_id"] == loaded.result_id
        actual.add(member["realization"]["basal_realization_id"])
    assert actual == expected
    with pytest.raises(FileExistsError):
        loaded.write(tmp_path / "result")
    for rank in (-1, 16, True):
        with pytest.raises(ValueError, match="rank"):
            loaded.member_json(case_id=case["case_id"], rank=rank, program_index=0)
    with pytest.raises(ValueError, match="case"):
        loaded.member_json(case_id="missing", rank=0, program_index=0)
    with pytest.raises(ValueError, match="program"):
        loaded.member_json(case_id=case["case_id"], rank=0, program_index=1)


def test_public_basal_loader_rejects_foreign_schema_and_changed_result(tmp_path):
    from hop_design.construction import (
        discover_basal_sequence_space,
        load_verified_basal_sequence_space,
    )

    source = tmp_path / "request.json"
    source.write_text('{"schema":"unrecognized"}')
    with pytest.raises(ValueError, match="schema"):
        discover_basal_sequence_space(source)
    with pytest.raises(ValueError, match="schema"):
        load_verified_basal_sequence_space(source)
    source.write_text(compact_request(canonical_request()).model_dump_json(by_alias=True))
    result = json.loads(discover_basal_sequence_space(source).json_bytes)
    result["cases"] = []
    result["admitted_count"] = result["candidate_count"] = 0
    source.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="replay"):
        load_verified_basal_sequence_space(source)
