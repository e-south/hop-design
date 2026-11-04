"""Exact endpoint contradictions exhaust locally without compiling handle words."""

import json

from hop_design import construction
from tests.support.context_completion import LIMITS, records, request


def test_empty_release_context_domain_is_recorded_and_replayed(tmp_path):
    path = request(tmp_path, "empty-endpoint", completion=True)
    data = json.loads(path.read_text())
    data["placements"] = [{"left_bp": 16, "right_bp": 6}]
    path.write_text(json.dumps(data))
    index = tmp_path / "index.sqlite"
    result = construction.evaluate_interface_survey(
        path, index, max_evaluations=10, continuation_batch_size=64, **LIMITS
    )
    assert result["termination_reason"] == "exhausted_enumeration"
    assert result["coverage"]["excluded_pairs"] == 1
    assert result["coverage"]["unresolved_pairs"] == 0
    rows = records(index)
    assert all(row["bundle"] is None for row in rows)
    assert all(not row.get("empty_basal_planes") for row in rows)
    admissions = [facts for row in rows for facts in row.get("end_pair_admission", {}).values()]
    assert admissions
    assert all(a["scope"] == "necessary_end_pair_relation" for a in admissions)
    assert all(not a["requested_pair_admitted"] for a in admissions)
    assert construction.verify_interface_survey(path, index)["coverage"] == result["coverage"]
