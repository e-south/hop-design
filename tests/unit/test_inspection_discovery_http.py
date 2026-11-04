"""Discovery actions retain local authorization and leave the pinned atlas intact."""

import json
import threading
from contextvars import ContextVar
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from hop_design.commands.construction.editor.server import EditorServer
from hop_design.commands.design.inspection import DesignInspectionSession


def test_discovery_http_is_authorized_and_independent_of_inspection_lock():
    session = object.__new__(DesignInspectionSession)
    session._lock = threading.RLock()
    session._state = {"token": "pin-token", "selection": {"identity": "pinned"}}
    session._transport_cohort = ContextVar("cohort", default=None)
    session._transport_format = ContextVar("format", default=None)
    original = json.loads(json.dumps(session._state))
    session.state = lambda: dict(session._state)
    calls = []
    job = {"id": "job", "status": "running"}

    def begin(request, **options):
        acquired = []

        def check_lock():
            owns = session._lock.acquire(blocking=False)
            acquired.append(owns)
            if owns:
                session._lock.release()

        probe = threading.Thread(target=check_lock)
        probe.start()
        probe.join(timeout=1)
        assert acquired == [True], "Discovery waited under the inspection lock"
        calls.append((request, options))
        return job

    def check_id(identity):
        if identity != "job":
            raise ValueError("superseded")
        return job

    session._discovery = SimpleNamespace(begin=begin, snapshot=check_id, stop=check_id)
    server = EditorServer(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def call(route, payload=None, *, authorized=True):
        headers = {}
        if payload is not None:
            headers = {"Content-Type": "application/json", "Origin": server.origin}
            if authorized:
                headers["X-HOP-Editor-Token"] = server.token
        request = Request(
            server.origin + route,
            data=None if payload is None else json.dumps(payload).encode(),
            headers=headers,
        )
        with urlopen(request, timeout=2) as response:
            return response.read()

    try:
        assert b"discoveryControls" in call("/discovery.js")
        payload = {
            "token": "pin-token",
            "request": {"stem_arm": "ACGT", "product": "hairpin"},
            "evaluations": 2,
        }
        with pytest.raises(HTTPError) as error:
            call("/api/start-discovery", payload, authorized=False)
        assert error.value.code == 403
        assert json.loads(call("/api/start-discovery", payload)) == job
        assert calls == [(payload["request"], {"evaluations": 2, "first_choices": None})]
        assert json.loads(call("/api/state")) == original
        for route in ("status", "stop"):
            assert (
                json.loads(call(f"/api/{route}-discovery", {"token": "older-pin", "job_id": "job"}))
                == job
            )
            with pytest.raises(HTTPError) as error:
                call(f"/api/{route}-discovery", {"token": "pin-token", "job_id": "not-owned"})
            assert error.value.code == 400
        assert json.loads(call("/api/state")) == original
        with pytest.raises(HTTPError):
            call("/api/start-discovery", {**payload, "directory": "/not-owned"})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert not thread.is_alive()
