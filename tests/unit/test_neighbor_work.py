"""Bounds are explicit failures, never empty search or preservation claims."""

from threading import Event

import pytest

from hop_design.design.construction.navigation.neighbor_work import (
    NeighborWork,
    check_neighbor_work,
)


@pytest.mark.parametrize("seconds", [0, -1, float("inf"), float("nan"), True, 301])
def test_neighbor_budget_rejects_invalid_bounds(seconds):
    with pytest.raises(ValueError, match="budget"):
        NeighborWork(seconds)


def test_neighbor_deadline_and_cancellation_are_distinct(monkeypatch):
    import hop_design.design.construction.navigation.neighbor_work as owner

    monkeypatch.setattr(owner, "monotonic", lambda: 100.0)
    stop = Event()
    work = NeighborWork(2, cancelled=stop)
    work.check()
    monkeypatch.setattr(owner, "monotonic", lambda: 102.0)
    with pytest.raises(ValueError, match="unresolved"):
        work.check()
    stop.set()
    with pytest.raises(ValueError, match="cancelled"):
        work.check()


def test_nested_preservation_checks_stop_and_do_not_leak_into_ordinary_queries():
    work = NeighborWork()
    with pytest.raises(ValueError, match="cancelled"), work.activate():
        work.cancelled.set()
        check_neighbor_work()
    check_neighbor_work()
