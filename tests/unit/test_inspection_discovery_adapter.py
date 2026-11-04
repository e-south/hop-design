"""The browser worker consumes public progress without inferring molecular coverage."""

from threading import Event
from types import SimpleNamespace

import pytest

from hop_design import construction
from hop_design.commands.design.inspection_discovery_worker import execute_discovery


@pytest.mark.parametrize("continue_saved", [False, True])
def test_worker_forwards_public_callbacks_and_committed_progress(
    tmp_path, monkeypatch, continue_saved
):
    messages = []
    closed = []
    connection = SimpleNamespace(send=messages.append, close=lambda: closed.append(True))
    stopped = Event()
    request = None if continue_saved else {"stem_arm": "ACGT", "product": "hairpin"}
    calls = []

    def operation(*args, **kwargs):
        calls.append((args, kwargs))
        assert not kwargs["should_stop"]()
        kwargs["on_progress"](
            construction.DiscoveryProgress(
                product="hairpin",
                phase="checkpointed",
                evaluations=3,
                new_evaluations=1,
                evaluation_budget=2,
            )
        )
        kwargs["on_progress"](
            construction.DiscoveryProgress(
                product="hairpin",
                phase="stopped",
                evaluations=3,
                new_evaluations=1,
                evaluation_budget=2,
                termination_reason="cancelled",
            )
        )
        return SimpleNamespace(
            explain=lambda: {"actions": ["continue_search"], "matching_preparations": 2}
        )

    monkeypatch.setattr(
        construction,
        "continue_design_discovery" if continue_saved else "discover_designs",
        operation,
    )
    execute_discovery(connection, stopped, tmp_path, request, 2, None)
    assert calls[0][0] == ((tmp_path,) if continue_saved else (request, tmp_path))
    assert messages[0]["progress"]["evaluations"] == 3
    assert messages[0]["progress"]["new_evaluations"] == 1
    assert messages[-1] == {
        "kind": "finished",
        "status": "cancelled",
        "message": None,
        "resumable": True,
        "matching_preparations": 2,
    }
    assert closed == [True]


def test_zero_snapshot_cancel_remains_continuable_without_invented_counts(tmp_path, monkeypatch):
    messages = []

    def cancelled(*args, **kwargs):
        (tmp_path / "intent").mkdir()
        raise construction.DiscoveryCancelled("Stopped before a first snapshot")

    monkeypatch.setattr(construction, "discover_designs", cancelled)
    execute_discovery(
        SimpleNamespace(send=messages.append, close=lambda: None), Event(), tmp_path, {}, 2, None
    )
    assert messages == [
        {
            "kind": "finished",
            "status": "cancelled",
            "message": "Stopped before a first snapshot",
            "resumable": True,
        }
    ]
