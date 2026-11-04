"""An owned render worker cannot queue work or survive a closed inspector."""

import multiprocessing
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event, RLock
from types import SimpleNamespace

import pytest

from hop_design.commands.design.inspection_worker import SingleWorker


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_timeout_must_be_finite_and_positive_without_starting_a_process(timeout):
    worker = SingleWorker(int)
    try:
        with pytest.raises(ValueError, match="finite and positive"):
            worker.call("3", timeout=timeout)
        assert worker._process is None
    finally:
        worker.close()


def test_crashed_worker_has_a_deadline_and_retry_uses_a_new_process():
    before = {p.pid for p in multiprocessing.active_children()}
    worker = SingleWorker(time.sleep)
    try:
        worker.call(0)
        owned = next(p for p in multiprocessing.active_children() if p.pid not in before)
        with ThreadPoolExecutor(max_workers=1) as executor:
            active = executor.submit(worker.call, 30, timeout=0.5)
            deadline = time.monotonic() + 2
            while not worker._busy.locked() and time.monotonic() < deadline:
                time.sleep(0.005)
            assert worker._busy.locked()
            os.kill(owned.pid, signal.SIGKILL)
            with pytest.raises(ValueError, match="stopped unexpectedly"):
                active.result(timeout=2)
        assert worker.call(0) is None
    finally:
        worker.close()
    assert {p.pid for p in multiprocessing.active_children()} == before


def test_worker_failure_is_explicit_and_next_call_can_recover():
    worker = SingleWorker(int)
    try:
        assert worker.call("3") == 3
        with pytest.raises(ValueError, match="invalid literal"):
            worker.call("not an integer")
        assert worker.call("4") == 4
    finally:
        worker.close()
    with pytest.raises(ValueError, match="closed"):
        worker.call("5")


def test_closing_active_worker_is_prompt_and_does_not_wait_for_the_job():
    before = {p.pid for p in multiprocessing.active_children()}
    worker = SingleWorker(time.sleep)
    worker.call(0)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(worker.call, 30)
            deadline = time.monotonic() + 2
            while not worker._busy.locked() and time.monotonic() < deadline:
                time.sleep(0.005)
            assert worker._busy.locked()
            with pytest.raises(ValueError, match="busy"):
                worker.call(0)
            start = time.monotonic()
            worker.close()
            with pytest.raises(ValueError, match="closed"):
                future.result(timeout=2)
            assert time.monotonic() - start < 2
    finally:
        worker.close()
    assert {p.pid for p in multiprocessing.active_children()} == before


def test_timed_out_worker_is_discarded_and_an_explicit_retry_starts_clean():
    before = {p.pid for p in multiprocessing.active_children()}
    worker = SingleWorker(time.sleep)
    try:
        worker.call(0)
        with pytest.raises(ValueError, match="timed out"):
            worker.call(30, timeout=0.1)
        assert worker.call(0) is None
    finally:
        worker.close()
    assert {p.pid for p in multiprocessing.active_children()} == before


def test_session_close_cancels_render_before_waiting_for_its_state_lock():
    from hop_design.commands.design.inspection import DesignInspectionSession

    worker = SingleWorker(time.sleep)
    worker.call(0)
    session = object.__new__(DesignInspectionSession)
    session._lock = RLock()
    session._neighbor_cancel, session._neighbor_done = Event(), Event()
    session._neighbor_done.set()
    session._state, session._undo, session._history = {}, [], []
    session._discovery = SimpleNamespace(close=lambda: None)
    session._cache = session._plots = SimpleNamespace(close=lambda: None)
    session._hover = SimpleNamespace(stop=worker.close, close=worker.close)
    entered = Event()

    def inspect():
        with session._lock:
            entered.set()
            worker.call(30)

    with ThreadPoolExecutor(max_workers=2) as executor:
        active = executor.submit(inspect)
        assert entered.wait(2)
        closing = executor.submit(session.close)
        try:
            closing.result(timeout=2)
        finally:
            worker.close()
        with pytest.raises(ValueError, match="closed"):
            active.result(timeout=2)
