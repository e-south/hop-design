"""Cooperative stopping preserves durable counts without inventing molecular evidence."""

import json
from types import SimpleNamespace

import pytest

from hop_design.design.construction.execution.feedback import DiscoveryCancelled, DiscoveryFeedback
from hop_design.design.construction.intents import hairpins
from hop_design.design.construction.intents.hairpin_history import validate_execution
from hop_design.models.construction.intents.execution import HairpinExecution
from tests.unit.test_construction_intent import STEM


def test_stop_before_first_candidate_has_no_empty_molecular_snapshot(tmp_path, monkeypatch):
    events = []

    def unexpected(*args, **kwargs):
        pytest.fail("An immediate stop must not start molecular discovery.")

    monkeypatch.setattr(hairpins, "_discover_with_receipts", unexpected)
    with pytest.raises(DiscoveryCancelled, match=r"[Rr]esum|continu"):
        hairpins.evaluate_hairpins(
            tmp_path,
            4,
            resolution=b'{"intent":{"product":"hairpin"}}',
            feedback=DiscoveryFeedback(events.append, lambda: True),
        )
    assert not (tmp_path / "hairpin-snapshots").exists()
    assert events[-1].phase == "stopped"
    assert events[-1].termination_reason == "cancelled"
    assert events[-1].evaluations == events[-1].new_evaluations == 0


def test_stop_before_next_page_returns_existing_choices(tmp_path, monkeypatch):
    previous = tmp_path / "previous"
    (previous / "branches/0000").mkdir(parents=True)
    (previous / "summary.json").write_text(json.dumps({"coverage": {"evaluated_pairs": 2}}))
    (previous / "branches/0000/summary.json").write_text(
        json.dumps({"coverage": {"recorded_pairs": 8}})
    )
    (previous / "manifest.json").write_text("{}")
    monkeypatch.setattr(hairpins, "snapshot_paths", lambda root: [previous])
    monkeypatch.setattr(
        hairpins, "snapshot_source", lambda root: (previous, SimpleNamespace(evaluated_pairs=2))
    )
    choices = object()
    monkeypatch.setattr(hairpins, "load_hairpin_choices", lambda *args: choices)
    events = []
    result = hairpins.evaluate_hairpins(
        tmp_path,
        4,
        resolution=b'{"intent":{"product":"adapter_ligated_hairpin"}}',
        feedback=DiscoveryFeedback(events.append, lambda: True),
    )
    assert result is choices
    assert events[-1].product == "adapter_ligated_hairpin"
    assert events[-1].evaluations == 2
    assert events[-1].new_evaluations == 0
    assert events[-1].termination_reason == "cancelled"
    assert not (tmp_path / "hairpin-snapshots").exists()


@pytest.mark.parametrize("schema,previous", [("v1", 0), ("v2", 7)])
def test_cancelled_execution_validates_only_a_nonempty_contiguous_partial_prefix(schema, previous):
    execution = HairpinExecution(
        schema=f"hop.hairpin-design-execution/{schema}",
        max_evaluations=4,
        previous_evaluated_pairs=previous,
        evaluated_pairs=previous + 2,
        previous_snapshot_digest="sha256:" + "0" * 64 if previous else None,
        snapshot_digest="sha256:" + "1" * 64,
        stopping_reason="cancelled",
    )
    options = {
        "coverage": {"recorded_pairs": previous + 8, "evaluated_pairs": 2},
        "candidates": [
            {"outcome": f"candidates/{i:04d}/outcome/report.md"}
            for i in range(previous, previous + 2)
        ],
        "options": [],
        **({"pair_window": {"start": previous, "stop": previous + 2}} if previous else {}),
    }
    validate_execution(execution, options)
    with pytest.raises(ValueError, match="stopping"):
        validate_execution(execution.model_copy(update={"max_evaluations": 2}), options)
    options["options"] = [
        {"selection": {"bundle_path": f"candidates/{previous + 1:04d}/outcome/construction"}}
    ]
    with pytest.raises(ValueError, match="stopping"):
        validate_execution(execution.model_copy(update={"first_choices": 1}), options)


def test_cancelled_execution_cannot_claim_a_zero_attempt_snapshot():
    with pytest.raises(ValueError, match=r"[Cc]ancel"):
        HairpinExecution(
            max_evaluations=4,
            previous_evaluated_pairs=0,
            evaluated_pairs=0,
            snapshot_digest="sha256:" + "1" * 64,
            stopping_reason="cancelled",
        )


@pytest.mark.parametrize("callback", ["on_progress", "should_stop"])
def test_callback_failure_is_not_silently_converted_to_cancellation(callback, tmp_path):
    class ObserverFailure(Exception):
        pass

    def interrupted(*args):
        raise ObserverFailure("observer failed")

    with pytest.raises(ObserverFailure, match="observer failed"):
        hairpins.evaluate_hairpins(
            tmp_path,
            4,
            resolution=b'{"intent":{"product":"hairpin"}}',
            feedback=DiscoveryFeedback(**{callback: interrupted}),
        )
    assert not (tmp_path / "hairpin-snapshots").exists()


def test_callback_cancellation_exception_is_not_a_requested_stop(tmp_path, monkeypatch):
    from hop_design import construction

    (tmp_path / "effort.json").write_text(
        json.dumps({"local_nodes": 1000, "local_realizations": 1000})
    )
    resolution = construction.resolve_design_request({"stem_arm": STEM, "product": "hairpin"})

    def interrupted(*args, **kwargs):
        raise DiscoveryCancelled("observer failure, not a returned stop request")

    monkeypatch.setattr(hairpins, "_discover_with_receipts", interrupted)
    events = []
    with pytest.raises(DiscoveryCancelled, match="observer failure"):
        hairpins.evaluate_hairpins(
            tmp_path,
            4,
            resolution=resolution.json_bytes,
            feedback=DiscoveryFeedback(events.append, lambda: False),
        )
    assert [event.phase for event in events] == ["searching"]
