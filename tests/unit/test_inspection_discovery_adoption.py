"""Result admission commits one same-server transition, or preserves the old inspector."""

import threading
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from hop_design.commands.design import inspection_discovery_actions as actions


class Work:
    def __init__(self, root):
        self.output_directory = root
        self.closed = False
        self.busy = False

    @contextmanager
    def inspectable_result(self, identity):
        if identity != "job":
            raise ValueError("superseded")
        self.busy = True
        try:
            yield self.output_directory / "branch"
        finally:
            self.busy = False

    def snapshot(self, identity=None):
        return {"id": "job", "status": "completed"}

    def close(self):
        self.closed = True


class Session:
    def __init__(self, choices, output):
        self._state = {"token": "new", "selection": None, "choices": {"paths": []}}
        self._lock = threading.RLock()
        self._discovery = Work(output)
        self.designs = choices
        self.root = output
        output.mkdir(parents=True)
        self.closed = False

    def _check(self, payload, required):
        if payload["token"] != self._state["token"]:
            raise ValueError("Stale inspection")

    def response(self, action, **kwargs):
        return action()

    def state(self):
        return {**self._state, "discovery_work": None}

    def select(self, payload):
        raise ValueError("Old pin is absent")

    def sample(self, payload):
        self._state["selection"] = {"materialized_realization_id": "new-preparation"}
        return self.state()

    def close(self, *, close_discovery=True):
        self.closed = True
        if close_discovery:
            self._discovery.close()


def fixture(tmp_path, monkeypatch):
    old = Session("old-choices", tmp_path / "old")
    old._state = {"token": "old", "selection": {"materialized_realization_id": "old-pin"}}
    server = SimpleNamespace(session=old, _inspection_transition=threading.Lock(), _closing=False)
    created = []

    def factory(choices, output):
        value = Session(choices, output)
        created.append(value)
        return value

    monkeypatch.setattr(actions, "DesignInspectionSession", factory)
    return old, server, created


def test_success_transfers_discovery_ownership_without_starting_another_server(
    tmp_path, monkeypatch
):
    old, server, created = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(actions.construction, "load_design_choices", lambda path: "new-choices")
    manager = old._discovery
    answer = actions.inspect_results(server, old, {"token": "old", "job_id": "job"})
    assert server.session is created[0]
    assert answer["selection"]["materialized_realization_id"] == "new-preparation"
    assert answer["discovery_work"]["id"] == "job"
    assert old.closed and not manager.closed
    assert server.session._discovery is manager
    assert not manager.busy
    server.session.close()
    assert manager.closed


def test_admission_failure_leaves_original_pin_and_resources_intact(tmp_path, monkeypatch):
    old, server, created = fixture(tmp_path, monkeypatch)

    def rejected(path):
        raise ValueError("Saved results failed admission")

    monkeypatch.setattr(actions.construction, "load_design_choices", rejected)
    with pytest.raises(ValueError, match="failed admission"):
        actions.inspect_results(server, old, {"token": "old", "job_id": "job"})
    assert server.session is old and not old.closed
    assert old._state["selection"]["materialized_realization_id"] == "old-pin"
    assert not old._discovery.closed and not old._discovery.busy
    assert not created


def test_pin_change_during_admission_rejects_late_transition_and_cleans_candidate(
    tmp_path, monkeypatch
):
    old, server, created = fixture(tmp_path, monkeypatch)

    def admitted(path):
        old._state["token"] = "newer-pin"
        return "new-choices"

    monkeypatch.setattr(actions.construction, "load_design_choices", admitted)
    with pytest.raises(ValueError, match="Stale"):
        actions.inspect_results(server, old, {"token": "old", "job_id": "job"})
    assert server.session is old and not old.closed
    assert created[0].closed
    assert not created[0].root.exists()
    assert not old._discovery.closed


def test_server_closure_during_admission_cannot_install_a_new_inspector(tmp_path, monkeypatch):
    old, server, created = fixture(tmp_path, monkeypatch)

    def admitted(path):
        server._closing = True
        return "new-choices"

    monkeypatch.setattr(actions.construction, "load_design_choices", admitted)
    with pytest.raises(ValueError, match="closed"):
        actions.inspect_results(server, old, {"token": "old", "job_id": "job"})
    assert server.session is old
    assert created[0].closed and not created[0].root.exists()


def test_selected_preparation_is_kept_when_present_in_new_pool(tmp_path, monkeypatch):
    old, server, created = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(actions.construction, "load_design_choices", lambda path: "new-choices")
    factory = actions.DesignInspectionSession

    def candidate(choices, output):
        value = factory(choices, output)
        value._state["choices"]["paths"] = [
            {"matches": True, "materialized_realization_id": "old-pin"}
        ]

        def select(payload):
            value._state["selection"] = {
                "materialized_realization_id": payload["materialized_realization_id"]
            }
            return value.state()

        value.select = select
        return value

    monkeypatch.setattr(actions, "DesignInspectionSession", candidate)
    answer = actions.inspect_results(server, old, {"token": "old", "job_id": "job"})
    assert answer["selection"]["materialized_realization_id"] == "old-pin"
    assert server.session is created[0]


def test_drawing_failure_cleans_only_candidate_and_keeps_old_session(tmp_path, monkeypatch):
    old, server, created = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(actions.construction, "load_design_choices", lambda path: "new-choices")
    factory = actions.DesignInspectionSession

    def broken(choices, output):
        value = factory(choices, output)

        def fail(payload):
            raise ValueError("Cannot render this preparation")

        value.sample = fail
        return value

    monkeypatch.setattr(actions, "DesignInspectionSession", broken)
    with pytest.raises(ValueError, match="Cannot render"):
        actions.inspect_results(server, old, {"token": "old", "job_id": "job"})
    assert server.session is old and not old.closed
    assert created[0].closed and not created[0].root.exists()
    assert not old._discovery.closed and not old._discovery.busy


def test_cleanup_notice_after_commit_returns_new_token_not_a_false_admission_error(
    tmp_path, monkeypatch
):
    old, server, created = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(actions.construction, "load_design_choices", lambda path: "new-choices")

    def slow_close(**kwargs):
        raise RuntimeError("Neighbor work did not stop")

    old.close = slow_close
    answer = actions.inspect_results(server, old, {"token": "old", "job_id": "job"})
    assert server.session is created[0]
    assert answer["token"] == "new"
    assert "cleanup" in answer["inspection_notice"]


def test_stale_inspection_rejects_before_loading_or_allocating(tmp_path, monkeypatch):
    old, server, created = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        actions.construction, "load_design_choices", lambda path: pytest.fail("Loaded stale work")
    )
    with pytest.raises(ValueError, match="Stale"):
        actions.inspect_results(server, old, {"token": "stale", "job_id": "job"})
    assert server.session is old and not created


def test_http_result_action_stays_on_the_same_server_and_returns_complete_new_state(
    tmp_path, monkeypatch
):
    import json
    from urllib.request import Request, urlopen

    from hop_design.commands.construction.editor.server import EditorServer

    old, _, created = fixture(tmp_path, monkeypatch)
    old.mode = "design"
    monkeypatch.setattr(actions.construction, "load_design_choices", lambda path: "new-choices")
    server = EditorServer(old, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(
            server.origin + "/api/inspect-discovery",
            data=json.dumps({"token": "old", "job_id": "job"}).encode(),
            headers={
                "Content-Type": "application/json",
                "Origin": server.origin,
                "X-HOP-Editor-Token": server.token,
                "X-HOP-Inspection": "compact-v1",
                "X-HOP-Cohort": "old-cohort",
            },
        )
        with urlopen(request, timeout=2) as response:
            answer = json.load(response)
        assert answer["token"] == "new"
        assert answer["selection"]["materialized_realization_id"] == "new-preparation"
        assert server.session is created[0]
        with urlopen(server.origin + "/api/state", timeout=2) as response:
            assert json.load(response)["selection"] == answer["selection"]
    finally:
        server.shutdown()
        server.server_close()
        server.session.close()
        thread.join(timeout=2)
    assert not thread.is_alive()
    assert old.closed and old._discovery.closed
