"""Browser selection uses the same exact query contract as CLI and API."""

import importlib
import json
from pathlib import Path

import pytest

from tests.support.interface_surveys import indexed_survey


def test_survey_session_preserves_preview_but_rejects_stale_or_excluded_selection(tmp_path):
    request, index = indexed_survey(tmp_path)
    session_type = importlib.import_module(
        "hop_design.commands.construction.editor.surveys"
    ).SurveySession
    session = session_type(request, index, tmp_path / "view")
    initial = session.state()
    assert initial["preview"] is None
    assert initial["choices"]["matching_preparations"] == 1
    selected = session.sample({"token": initial["token"], "seed": 17})
    exact = selected["selection"]
    assert selected["preview"]["summary"]["selection"] == exact
    assert selected["preview_status"] == "compatible"
    assert len(selected["preview"]["summary"]["atlas"]["states"]) == 11
    old_token = selected["token"]
    narrowed = session.query(
        {
            "token": old_token,
            "query": {"parameters": [{"key": "left_end_word", "values": ["TGCA"]}]},
        }
    )
    assert narrowed["preview"] == selected["preview"]
    assert narrowed["preview_status"] == "excluded_by_query"
    assert narrowed["selection"] is None
    assert narrowed["choices"]["matching_preparations"] == 0
    with pytest.raises(ValueError, match="Stale"):
        session.sample({"token": old_token, "seed": 17})
    with pytest.raises(ValueError, match=r"match|eligible"):
        session.sample({"token": narrowed["token"], "seed": 17})
    with pytest.raises(ValueError, match="Select"):
        session.retrieve({"token": narrowed["token"], "selection": exact})
    restored = session.query({"token": narrowed["token"], "query": {}})
    assert (
        restored["preview"]["summary"]["projection"] == selected["preview"]["summary"]["projection"]
    )
    assert (
        restored["selection"]["materialized_realization_id"] == exact["materialized_realization_id"]
    )
    receipt = session.retrieve({"token": restored["token"], "selection": restored["selection"]})
    assert receipt["handoff"]["selection"] == restored["selection"]
    folder = session.root / receipt["handoff"]["directory"]
    assert json.loads((folder / "selection.json").read_text()) == restored["selection"]
    assert (session.root / receipt["handoff"]["archive"].removeprefix("/files/")).is_file()
    copied = session.state()
    copied["choices"]["paths"].clear()
    assert session.state()["choices"]["paths"]
    assert Path(request).is_file() and Path(index).is_file()


def test_survey_http_has_one_selection_surface_and_keeps_transport_guards(tmp_path):
    import threading
    from urllib.error import HTTPError

    from tests.integration.test_molecular_editor_http import call

    request, index = indexed_survey(tmp_path)
    module = importlib.import_module("hop_design.commands.construction.editor.server")
    server = module.create_survey_server(request, index, tmp_path / "browser", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        page = call(server, "/")
        assert b"Designs around your stem" in page
        assert b"__SESSION_TOKEN__" not in page
        for route in (
            "/editor.js",
            "/editor.css",
            "/plot.js",
            "/model.js",
            "/atlas.js",
            "/atlas_position.js",
            "/parameters.js",
            "/camera_geometry.js",
        ):
            assert call(server, route)
        with pytest.raises(HTTPError) as error:
            call(server, "/api/state", host="foreign.example")
        assert error.value.code == 403
        initial = call(server, "/api/state")
        body = {"token": initial["token"], "seed": 17}
        with pytest.raises(HTTPError) as error:
            call(server, "/api/sample", body, authenticated=False)
        assert error.value.code == 403
        result = call(server, "/api/sample", body)
        assert call(server, result["preview"]["drawing"]).startswith(b"<svg")
        for route in ("/api/evaluate", "/api/evaluate-envelope", "/api/compare"):
            with pytest.raises(HTTPError) as error:
                call(server, route, {"token": result["token"]})
            assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            call(server, "/files/%2E%2E/request.json")
        assert error.value.code == 400
        (server.session.root / "escape").symlink_to(request)
        with pytest.raises(HTTPError) as error:
            call(server, "/files/escape")
        assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        server.session.close()
        thread.join(timeout=5)


def test_eligible_query_rebinds_the_atlas_receipt_to_the_current_selection(tmp_path):
    request, index = indexed_survey(tmp_path)
    from hop_design.commands.construction.editor.surveys import SurveySession

    session = SurveySession(request, index, tmp_path / "view")
    selected = session.sample({"token": session.state()["token"], "seed": 1})
    result = session.query(
        {
            "token": selected["token"],
            "query": {"parameters": [{"key": "left_end_word", "values": ["AGTC"]}]},
        }
    )
    assert result["selection"]["query"] == result["choices"]["query"]
    assert result["preview"]["summary"]["selection"] == result["selection"]


@pytest.mark.parametrize("action", ["query", "reload"])
def test_failed_rebind_does_not_advance_browser_state(tmp_path, monkeypatch, action):
    from hop_design import construction
    from hop_design.commands.construction.editor.surveys import SurveySession

    request, index = indexed_survey(tmp_path)
    session = SurveySession(request, index, tmp_path / "view")
    before = session.sample({"token": session.state()["token"], "seed": 1})
    if action == "reload":
        construction.evaluate_interface_survey(
            request,
            index,
            max_evaluations=1,
            local_nodes=100,
            local_realizations=16,
            release_site_pairs=100,
            resume=True,
        )

    def failed(*args, **kwargs):
        raise ValueError("deliberate replay failure")

    monkeypatch.setattr(construction, "inspect_interface_survey_atlas", failed)
    payload = {"token": before["token"]}
    if action == "query":
        payload["query"] = {"parameters": [{"key": "left_end_word", "values": ["AGTC"]}]}
    with pytest.raises(ValueError, match="deliberate replay"):
        getattr(session, action)(payload)
    assert session.state() == before
    assert session.pool.query()["snapshot_digest"] == before["choices"]["snapshot_digest"]
