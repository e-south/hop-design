"""One hard auxiliary family must not monopolize other supported search assignments."""

import json

from hop_design import construction
from tests.support.context_completion import LIMITS, records, request


def hard_request(tmp_path):
    path = request(tmp_path, "hard", completion=True)
    data = json.loads(path.read_text())
    preparation = data["materialization"]["source_preparation"]
    preparation["source_ssdna"]["upstream_sequence_spec"] = "N" * 14
    preparation["forward_primer"] = {
        "mode": "fixed",
        "primer": {
            "annealing_length_nt": 14,
            "oligo": {
                "sequence_5prime": "T" * 14,
                "five_prime_end": "hydroxyl",
                "three_prime_end": "hydroxyl",
            },
        },
    }
    path.write_text(json.dumps(data))
    return path


def test_hard_handles_do_not_monopolize_group_discovery(tmp_path):
    path = hard_request(tmp_path)
    index = tmp_path / "hard.sqlite"
    result = construction.evaluate_interface_survey(path, index, max_evaluations=14, **LIMITS)
    attempts = [r for r in records(index) if r.get("bundle")]
    groups = {
        (r["completion"]["geometry_rank"], r["completion"]["page"], r["completion"]["group"])
        for r in attempts
    }
    assert len(groups) >= 3
    assert all(not r["group_pair_resolved"] for r in attempts)
    assert result["coverage"]["excluded_pairs"] == 0
    assert result["coverage"]["unresolved_pairs"] == 1
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 14


def test_hard_completion_cold_resume_keeps_the_same_pending_work(tmp_path):
    path = hard_request(tmp_path)
    resumed, continuous = tmp_path / "resumed.sqlite", tmp_path / "continuous.sqlite"
    construction.evaluate_interface_survey(path, resumed, max_evaluations=6, **LIMITS)
    construction.evaluate_interface_survey(path, resumed, max_evaluations=8, resume=True, **LIMITS)
    construction.evaluate_interface_survey(path, continuous, max_evaluations=14, **LIMITS)
    assert records(resumed) == records(continuous)
