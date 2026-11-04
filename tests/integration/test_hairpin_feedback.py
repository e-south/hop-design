"""Cancelled hairpin work is a replayable prefix under the ordinary public lifecycle."""

import json

import pytest

from hop_design import construction
from hop_design.design.construction.execution.feedback import DiscoveryCancelled
from tests.unit.test_construction_intent import STEM


def test_cancelled_hairpin_prefix_replays_and_resumes_exactly(tmp_path, monkeypatch):
    import hop_design.design.construction.options.explore as owner

    attempts = []
    original = owner.evaluate_candidate

    def observed(*args, **kwargs):
        receipt = original(*args, **kwargs)
        attempts.append(kwargs["design_id"])
        return receipt

    monkeypatch.setattr(owner, "evaluate_candidate", observed)
    root = tmp_path / "cancelled"
    events = []

    def progress(event):
        events.append(event)
        if event.phase == "searching":
            assert event.evaluations == event.new_evaluations == 0
            assert not (root / "hairpin-snapshots/0000").exists()
        else:
            execution = json.loads((root / "hairpin-snapshots/0000/execution.json").read_bytes())
            assert event.evaluations == execution["evaluated_pairs"] == 2
            assert event.new_evaluations == 2

    request = {"stem_arm": STEM, "product": "hairpin"}
    first = construction.discover_designs(
        request,
        root,
        max_evaluations=4,
        on_progress=progress,
        should_stop=lambda: len(attempts) == 2,
    )
    assert len(attempts) == 2
    assert [event.phase for event in events] == ["searching", "checkpointed", "stopped"]
    assert events[-1].termination_reason == "cancelled"
    assert first.query()["execution"]["stopping_reason"] == "cancelled"
    reopened = construction.load_design_choices(root)
    assert reopened.query() == first.query()
    resumed = reopened.find_more(max_evaluations=2)
    assert len(attempts) == len(set(attempts)) == 4
    uninterrupted = construction.discover_designs(request, tmp_path / "whole", max_evaluations=4)
    assert resumed.query()["paths"] == uninterrupted.query()["paths"]
    assert resumed.query()["coverage"] == uninterrupted.query()["coverage"]


def test_late_zero_work_cancel_preserves_intent_without_false_empty_choices(tmp_path):
    root = tmp_path / "before-first-candidate"
    stops = []
    events = []

    def should_stop():
        stops.append(True)
        return len(stops) > 1

    with pytest.raises(DiscoveryCancelled, match="continue"):
        construction.discover_designs(
            {"stem_arm": STEM, "product": "hairpin"},
            root,
            max_evaluations=2,
            on_progress=events.append,
            should_stop=should_stop,
        )
    assert (root / "intent/request.json").exists()
    assert not (root / "hairpin-snapshots").exists()
    assert events[-1].termination_reason == "cancelled"
    assert events[-1].evaluations == 0
    resumed = construction.continue_design_discovery(root, max_evaluations=2)
    assert resumed.query()["coverage"]["evaluated_pairs"] == 2


def test_checkpoint_observer_failure_leaves_a_reopenable_snapshot(tmp_path):
    root = tmp_path / "observer-failure"

    def interrupted(event):
        if event.phase == "checkpointed":
            raise RuntimeError("observer interrupted after commit")

    with pytest.raises(RuntimeError, match="observer interrupted"):
        construction.discover_designs(
            {"stem_arm": STEM, "product": "hairpin"},
            root,
            max_evaluations=2,
            on_progress=interrupted,
        )
    reopened = construction.load_design_choices(root)
    assert reopened.query()["coverage"]["evaluated_pairs"] == 2
    assert reopened.query()["execution"]["stopping_reason"] == "evaluation_limit"
