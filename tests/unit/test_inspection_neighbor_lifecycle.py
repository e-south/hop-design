"""Slow neighbor work must not own inspection or teardown locks."""

from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from threading import Event, Lock, RLock
from types import SimpleNamespace

import pytest

from hop_design.api import _InspectionProjection
from hop_design.commands.design.inspection import DesignInspectionSession
from hop_design.commands.design.inspection_hover import cancel_neighbors, neighboring_preparations


def test_neighbor_cancel_releases_work_without_owning_inspection_lock(monkeypatch):
    session = object.__new__(DesignInspectionSession)
    session._lock = RLock()
    session._transport_cohort = ContextVar("test_cohort", default=None)
    session._transport_format = ContextVar("test_format", default=None)
    session._neighbor_cancel = Event()
    session._neighbor_lock = Lock()
    session._neighbor_done = Event()
    session._state = {
        "token": "token",
        "choices": {"query": {}},
        "selection": {"materialized_realization_id": "reference"},
    }
    session._undo, session._history = [], []
    session._discovery = SimpleNamespace(close=lambda: None)
    session._cache = session._plots = session._hover = SimpleNamespace(
        close=lambda: None, stop=lambda: None
    )
    session.designs = SimpleNamespace()
    started = Event()

    def slow(*args, work, **kwargs):
        started.set()
        assert work.cancelled.wait(timeout=2), "closing did not cancel neighbor work"
        work.check()

    monkeypatch.setattr(_InspectionProjection, "neighbors", slow, raising=False)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            session.response,
            lambda: neighboring_preparations(session, {"token": "token"}),
            cohort="worker-cohort",
        )
        assert started.wait(timeout=2)
        acquired = session._lock.acquire(blocking=False)
        try:
            assert acquired, "neighbor computation blocked ordinary inspection"
            assert session._transport_cohort.get() is None
            session.close()
        finally:
            if acquired:
                session._lock.release()
        with pytest.raises(ValueError, match="cancelled"):
            future.result(timeout=2)


def test_late_cancel_does_not_stop_a_newer_neighbor_request():
    session = object.__new__(DesignInspectionSession)
    session._lock = RLock()
    session._state = {"token": "token"}
    session._neighbor_cancel = Event()
    session._neighbor_request = "new"
    assert cancel_neighbors(session, {"token": "token", "request_id": "old"}) == {
        "status": "superseded"
    }
    assert not session._neighbor_cancel.is_set()
    assert cancel_neighbors(session, {"token": "token", "request_id": "new"}) == {
        "status": "cancelled"
    }
    assert session._neighbor_cancel.is_set()
