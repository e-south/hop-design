"""The public discovery API shares constraints without losing resume or replay."""

import json

from hop_design import construction
from hop_design.design.construction.surveys.completion.shared_screen import BasalScreen
from tests.support.context_completion import LIMITS, records, request


def shared_request(tmp_path):
    path = request(tmp_path, "shared", completion=True)
    data = json.loads(path.read_text())
    data["targets"]["right_words"].append("TTTT")
    path.write_text(json.dumps(data))
    return path


def test_public_shared_screen_cold_resume_and_molecular_replay(tmp_path):
    path = shared_request(tmp_path)
    resumed, full = tmp_path / "resumed.sqlite", tmp_path / "full.sqlite"
    first = construction.evaluate_interface_survey(path, resumed, max_evaluations=4, **LIMITS)
    assert first["shared_end_pair_screen"]["frames"] == 1
    assert first["shared_end_pair_screen"]["unknown_frames"] == 0
    continued = construction.evaluate_interface_survey(
        path, resumed, max_evaluations=4, resume=True, **LIMITS
    )
    uninterrupted = construction.evaluate_interface_survey(path, full, max_evaluations=8, **LIMITS)
    assert continued["coverage"] == uninterrupted["coverage"]
    assert records(resumed) == records(full)
    assert any(record["witnesses"] for record in records(resumed))
    assert construction.verify_interface_survey(path, resumed)["coverage"] == continued["coverage"]


def test_cancellation_during_screen_keeps_targets_unresolved_and_can_resume(tmp_path, monkeypatch):
    path = shared_request(tmp_path)
    index = tmp_path / "cancelled.sqlite"
    original = BasalScreen.build.__func__
    inside_screen = False

    def entering(cls, *args, **kwargs):
        nonlocal inside_screen
        inside_screen = True
        return original(cls, *args, **kwargs)

    monkeypatch.setattr(BasalScreen, "build", classmethod(entering))
    result = construction.evaluate_interface_survey(
        path, index, max_evaluations=4, should_stop=lambda: inside_screen, **LIMITS
    )
    assert result["termination_reason"] == "cancelled"
    assert result["evaluations"] == 0
    assert result["coverage"]["excluded_pairs"] == 0
    assert result["coverage"]["unresolved_pairs"] == 2
    resumed = construction.evaluate_interface_survey(
        path, index, max_evaluations=4, resume=True, **LIMITS
    )
    assert resumed["new_evaluations"] > 0
