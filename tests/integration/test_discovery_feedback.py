"""Progress reports committed work; cooperative stopping preserves exact continuation."""

import json

import pytest

from hop_design import construction
from tests.support.context_completion import LIMITS, records, request


def test_survey_feedback_stops_after_commit_and_resumes_same_prefix(tmp_path):
    path = request(tmp_path, "feedback", completion=True)
    index = tmp_path / "stopped.sqlite"
    events = []

    def observe(event):
        events.append(event)
        assert len(records(index)) == event.evaluations

    result = construction.evaluate_interface_survey(
        path,
        index,
        max_evaluations=2,
        on_progress=observe,
        should_stop=lambda: any(e.new_evaluations == 1 for e in events),
        **LIMITS,
    )
    assert result["termination_reason"] == "cancelled"
    assert result["new_evaluations"] == 1
    assert [e.phase for e in events] == ["searching", "checkpointed", "stopped"]
    assert [e.evaluations for e in events] == [0, 1, 1]
    assert events[-1].termination_reason == "cancelled"
    assert events[-1].product == "released_insert"
    assert events[-1].evaluation_budget == 2
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 1

    construction.evaluate_interface_survey(path, index, max_evaluations=1, resume=True, **LIMITS)
    whole = tmp_path / "whole.sqlite"
    construction.evaluate_interface_survey(path, whole, max_evaluations=2, **LIMITS)
    assert records(index) == records(whole)


def test_optional_intent_feedback_preserves_query_and_zero_work_stop(tmp_path):
    path = request(tmp_path, "intent-feedback", completion=True)
    native = json.loads(path.read_bytes())
    context = {
        key: value
        for key, value in native.items()
        if key not in {"schema", "stem_arm", "targets", "name"}
    }
    context.update(
        schema="hop.construction-context/v1",
        context_id="feedback/v1",
        description="Synthetic feedback example.",
        product="released_insert",
    )
    intent = {
        "stem_arm": native["stem_arm"],
        "product": "released_insert",
        "context": context,
        "ends": {"left": "AGTC", "right": "AGTC"},
    }
    events = []
    stopped = construction.discover_designs(
        intent,
        tmp_path / "intent",
        effort=LIMITS,
        max_evaluations=2,
        on_progress=events.append,
        should_stop=lambda: True,
    )
    assert stopped.query()["matching_preparations"] == 0
    assert events[-1].termination_reason == "cancelled"
    assert events[-1].evaluations == 0
    resumed = stopped.find_more(max_evaluations=2, on_progress=events.append)
    assert events[-1].evaluations == 2
    whole = construction.discover_designs(
        intent, tmp_path / "normal", effort=LIMITS, max_evaluations=2
    )
    assert resumed.query() == whole.query()


def test_callback_failure_keeps_committed_checkpoint_readable(tmp_path):
    path = request(tmp_path, "observer", completion=True)
    index = tmp_path / "observer.sqlite"

    def broken(event):
        if event.phase == "checkpointed":
            raise RuntimeError("observer failed")

    with pytest.raises(RuntimeError, match="observer failed"):
        construction.evaluate_interface_survey(
            path, index, max_evaluations=2, on_progress=broken, **LIMITS
        )
    assert len(records(index)) == 1
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 1


def test_invalid_feedback_fails_explicitly_before_evaluation(tmp_path):
    path = request(tmp_path, "invalid-feedback", completion=True)
    index = tmp_path / "invalid.sqlite"
    with pytest.raises(TypeError, match="callable"):
        construction.evaluate_interface_survey(
            path, index, max_evaluations=1, on_progress=42, **LIMITS
        )
    assert not index.exists()
    with pytest.raises(TypeError, match="Boolean"):
        construction.evaluate_interface_survey(
            path, index, max_evaluations=1, should_stop=lambda: 1, **LIMITS
        )
    assert records(index) == []
