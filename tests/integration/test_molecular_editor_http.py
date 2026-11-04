"""The local editor uses the public edit workflow and rejects unsafe or stale requests."""

import importlib
import json
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from tests.integration.test_molecular_edits import loop_request


@pytest.fixture
def editor(tmp_path):
    module = importlib.import_module("hop_design.commands.construction.editor.server")
    server = module.create_editor_server(loop_request(tmp_path), tmp_path / "editor", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    server.session.close()
    thread.join(timeout=5)


def call(server, route, body=None, *, authenticated=True, host=None, cohort=None):
    headers = {}
    if body is not None:
        headers.update({"Content-Type": "application/json", "Origin": server.origin})
        if authenticated:
            headers["X-HOP-Editor-Token"] = server.token
    if host:
        headers["Host"] = host
    if cohort is not None:
        headers["X-HOP-Cohort"] = cohort
    request = Request(
        server.origin + route,
        data=None if body is None else json.dumps(body).encode(),
        headers=headers,
    )
    with urlopen(request, timeout=20) as response:
        data = response.read()
        return json.loads(data) if "json" in response.headers.get("Content-Type", "") else data


def test_editor_requires_local_origin_and_explicit_authorized_preview(editor):
    page = call(editor, "/")
    assert b"Edit the scaffold" in page
    assert b"keyboard" in page.lower()
    with pytest.raises(HTTPError) as error:
        call(editor, "/api/preview", {"loop_sequences": ["TTTC"]}, authenticated=False)
    assert error.value.code == 403
    with pytest.raises(HTTPError) as error:
        call(editor, "/api/state", host="foreign.example")
    assert error.value.code == 403
    with pytest.raises(HTTPError) as error:
        call(editor, "/api/preview", {"loop_sequences": ["TTTC"], "relax": True})
    assert error.value.code == 400
    preview = call(editor, "/api/preview", {"loop_sequences": ["GAAA", "TTTC"]})
    assert preview["preview"]["status"] == "ready"
    assert preview["result"] is None
    assert preview["preview"]["execution"] == "not_started"


def test_editor_surfaces_unexpected_worker_failure(editor, monkeypatch):
    from hop_design import construction

    def failed(_):
        raise RuntimeError("deliberate test failure")

    monkeypatch.setattr(construction, "execute_molecular_edit", failed)
    state = call(editor, "/api/preview", {"loop_sequences": ["GAAA"]})
    call(editor, "/api/evaluate", {"edit_digest": state["preview"]["edit_digest"]})
    deadline = time.monotonic() + 5
    while (state := call(editor, "/api/state"))["busy"]:
        assert time.monotonic() < deadline
        time.sleep(0.05)
    assert "deliberate test failure" in state["error"]
    assert state["result"] is None


def test_editor_evaluates_then_rejects_selection_after_another_edit(editor):
    preview = call(editor, "/api/preview", {"loop_sequences": ["GAAA", "TTTC"]})
    digest = preview["preview"]["edit_digest"]
    call(editor, "/api/evaluate", {"edit_digest": digest})
    deadline = time.monotonic() + 60
    while True:
        state = call(editor, "/api/state")
        if not state["busy"]:
            break
        assert time.monotonic() < deadline, "Editor evaluation did not finish"
        time.sleep(0.1)
    assert state["error"] is None, state
    assert len(state["result"]["options"]) == 2
    members = {f"member-{i}": o["label"] for i, o in enumerate(state["result"]["options"])}
    selected = call(
        editor,
        "/api/select",
        {
            "edit_digest": digest,
            "members": members,
            "baseline": "member-0",
            "shared_properties": ["non_loop_sequences"],
        },
    )
    assert selected["selection"]["archive"].endswith(".zip")
    assert call(editor, selected["selection"]["archive"]).startswith(b"PK")
    call(editor, "/api/preview", {"loop_sequences": ["GAAA"]})
    with pytest.raises(HTTPError) as error:
        call(
            editor,
            "/api/select",
            {
                "edit_digest": digest,
                "members": members,
                "baseline": "member-0",
                "shared_properties": [],
            },
        )
    assert error.value.code == 400
