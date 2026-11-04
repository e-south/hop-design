"""Survey navigation uses necessary relations without claiming local or route support."""

import json

from hop_design import construction
from tests.support.context_completion import LIMITS, records, request


def test_incompatible_end_pair_excludes_before_local_construction_and_replays(tmp_path):
    path = request(tmp_path, "end-pair-conflict", completion=True)
    data = json.loads(path.read_text())
    data["placements"] = [{"left_bp": 6, "right_bp": 6}]
    data["targets"] = {"left_words": ["AAAA"], "right_words": ["AAAC"]}
    # Canonical contacts require equal own-strand end words at these placements.
    data["basal"]["geometry"]["max_noncanonical_pairs"] = 0
    for c in data["basal"]["geometry"]["pairing_constraints"]:
        c["allowed_class"] = "match"
    path.write_text(json.dumps(data))
    index = tmp_path / "index.sqlite"
    result = construction.evaluate_interface_survey(
        path, index, max_evaluations=20, continuation_batch_size=64, **LIMITS
    )
    assert result["termination_reason"] == "exhausted_enumeration"
    assert result["coverage"]["excluded_pairs"] == 1
    rows = records(index)
    assert all(r["bundle"] is None and not r.get("empty_basal_planes") for r in rows)
    facts = [a for r in rows for a in r.get("end_pair_admission", {}).values()]
    assert facts and all(a["scope"] == "necessary_end_pair_relation" for a in facts)
    assert all(a["requested_pair_admitted"] is False for a in facts)
    assert construction.verify_interface_survey(path, index)["coverage"] == result["coverage"]
