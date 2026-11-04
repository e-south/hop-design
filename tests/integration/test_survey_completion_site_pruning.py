"""Exact source conflicts skip a conditional subset, never all later handles."""

import json

from hop_design import construction
from tests.support.context_completion import LIMITS, records, request


def test_invariant_source_conflict_resolves_group_after_one_full_compile(tmp_path):
    path = request(tmp_path, "fixed-conflict", completion=True)
    data = json.loads(path.read_text())
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "CATTGCNNAGTCGTAC"
    )
    path.write_text(json.dumps(data))
    index = tmp_path / "index.sqlite"
    result = construction.evaluate_interface_survey(path, index, max_evaluations=2, **LIMITS)
    last = records(index)[-1]
    assert last["outcome"]["rejection_reasons"] == ["global-actionable-site-conflict"]
    assert last["group_completion_count"] == 16
    assert last["group_pair_resolved"]
    assert "completion_seek" in last["next"] or last["next"]["completion"]["pair"] > 0
    assert result["coverage"]["excluded_pairs"] == 0
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 2


def test_source_conflict_skips_many_words_but_keeps_later_valid_handle(tmp_path):
    path = request(tmp_path, "conditional-conflict", completion=True)
    data = json.loads(path.read_text())
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "CWTTGCNNAGTCGTAC"
    )
    path.write_text(json.dumps(data))
    index = tmp_path / "index.sqlite"
    construction.evaluate_interface_survey(path, index, max_evaluations=2, **LIMITS)
    last = records(index)[-1]
    assert not last["group_pair_resolved"]
    # The first 16 words have the unintended CATTGC site. CTTTGC can remove it.
    pending = [
        e["work"] for e in last["next"]["completion_seek"]["frontier"] if e["kind"] == "work"
    ]
    assert any(w["pair"] == 0 and w["member"] == 16 for w in pending)
    later = construction.evaluate_interface_survey(
        path, index, max_evaluations=2, resume=True, **LIMITS
    )
    assert later["coverage"]["supported_pairs"] == 1
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 4
