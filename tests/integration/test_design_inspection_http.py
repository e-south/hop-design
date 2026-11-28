"""
--------------------------------------------------------------------------------
HOP Design
hop-design/tests/integration/test_design_inspection_http.py

Check inspection selection, validation and HTTP transport behavior.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
import threading
from urllib.error import HTTPError

import pytest

from hop_design.commands.construction.editor.server import EditorServer
from hop_design.commands.design.inspection import DesignInspectionSession
from tests.integration.test_atlas_edition import captured_choices, captured_edition  # noqa: F401
from tests.integration.test_molecular_editor_http import call


def test_malformed_saved_view_returns_json_error_without_changing_the_session(
    captured_edition,  # noqa: F811
    tmp_path,
):
    session = DesignInspectionSession(captured_edition, tmp_path / "malformed-view")
    server = EditorServer(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        initial = call(server, "/api/state")
        selected = call(server, "/api/sample", {"token": initial["token"], "seed": 0})
        for field in ("presentation", "exploration"):
            for raw in (False, 0, [], "invalid"):
                with pytest.raises(ValueError, match=f"{field.capitalize()} must be a JSON object"):
                    captured_edition.view(selected["selection"], **{field: raw})
        for raw in (None, False, True, 0, "saved", [], [{}]):
            message = (
                "HOP source is not a regular file: saved."
                if isinstance(raw, str)
                else "Saved view must be a JSON object."
            )
            with pytest.raises(HTTPError) as failure:
                call(server, "/api/restore", {"token": selected["token"], "receipt": raw})
            assert failure.value.code == 400
            assert json.loads(failure.value.read())["error"] == message
            assert call(server, "/api/state") == selected
            with pytest.raises(ValueError, match=message):
                captured_edition.restore_view(raw)
        restored = call(
            server,
            "/api/restore",
            {"token": selected["token"], "receipt": selected["view_receipt"]},
        )
        assert restored["selection"] == selected["selection"]
        assert restored["view_receipt"] == selected["view_receipt"]
    finally:
        server.shutdown()
        server.server_close()
        session.close()
        thread.join(timeout=5)


def test_invalid_view_file_is_rejected_before_creating_browser_output(
    captured_edition,  # noqa: F811
    tmp_path,
):
    from hop_design.commands.design.browser import create_design_server

    receipt = tmp_path / "invalid-view.json"
    receipt.write_text("null")
    output = tmp_path / "new-browser"
    with pytest.raises(ValueError, match="root must be a mapping"):
        create_design_server(captured_edition._directory, output, receipt=receipt)
    assert not output.exists(), "A corrected view must be able to retry the same output path"


def test_invalid_sampling_strategy_returns_json_error_and_preserves_selection(
    captured_edition,  # noqa: F811
    tmp_path,
):
    session = DesignInspectionSession(captured_edition, tmp_path / "invalid-strategy")
    server = EditorServer(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        initial = call(server, "/api/state")
        selected = call(server, "/api/sample", {"token": initial["token"], "seed": 0})
        for strategy in ([], {}, False, 0, "", "unknown"):
            with pytest.raises(ValueError, match="Sampling strategy must be"):
                captured_edition.sample(seed=0, strategy=strategy)
            with pytest.raises(HTTPError) as failure:
                call(
                    server,
                    "/api/sample",
                    {"token": selected["token"], "seed": 0, "strategy": strategy},
                )
            assert failure.value.code == 400
            assert "Sampling strategy must be" in json.loads(failure.value.read())["error"]
            assert call(server, "/api/state") == selected
        expected = captured_edition.sample(seed=0, strategy="preparations")
        retried = call(
            server,
            "/api/sample",
            {"token": selected["token"], "seed": 0, "strategy": "preparations"},
        )
        assert retried["selection"] == expected
    finally:
        server.shutdown()
        server.server_close()
        session.close()
        thread.join(timeout=5)


def test_shared_http_preserves_query_and_rejects_unauthorized_actions(captured_edition, tmp_path):  # noqa: F811
    session = DesignInspectionSession(captured_edition, tmp_path / "view")
    server = EditorServer(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert b"Show me another" in call(server, "/")
        for asset in (
            "editor.js",
            "editor.css",
            "landscape.js",
            "member_choices.js",
            "atlas.js",
            "teaching_links.js",
            "local_choices.js",
            "hover_preview.js",
            "map_camera.js",
            "neighbors.js",
            "panel_status.js",
            "inspection_loading.js",
            "indexed_map.js",
            "map_index.js",
            "molecular_colors.js",
            "color_controls.js",
            "inspection_facts.js",
            "route_scenes.js",
            "route_scene_work.js",
            "inspector_resize.js",
        ):
            assert call(server, "/" + asset)
        initial = call(server, "/api/state")
        assert initial["feature_parameters"] == captured_edition.parameters()
        with pytest.raises(HTTPError) as error:
            call(server, "/api/sample", {"token": initial["token"], "seed": 0}, authenticated=False)
        assert error.value.code == 403
        selected = call(
            server, "/api/sample", {"token": initial["token"], "seed": 0, "strategy": "families"}
        )
        hover_request = {
            "token": selected["token"],
            "materialized_realization_id": selected["selection"]["materialized_realization_id"],
        }
        with pytest.raises(HTTPError) as error:
            call(server, "/api/preview", hover_request, authenticated=False)
        assert error.value.code == 403
        hover = call(server, "/api/preview", hover_request)
        assert hover["token"] == selected["token"]
        assert call(server, hover["molecule"])
        assert hover["trace"]["projection"] == selected["trace_projection"]["projection"]
        assert call(server, "/api/state")["selection"] == selected["selection"]
        scene_request = {**hover_request, "phases": ["duplex"]}
        with pytest.raises(HTTPError) as error:
            call(server, "/api/scenes", scene_request, authenticated=False)
        assert error.value.code == 403
        scenes = call(server, "/api/scenes", scene_request)
        assert scenes["materialized_realization_id"] == hover["materialized_realization_id"]
        assert call(server, scenes["scenes"][0]["drawing"])
        assert call(server, "/api/state")["selection"] == selected["selection"]
        assert (
            call(server, "/api/neighbors", {"token": selected["token"]})["reference_identity"]
            == hover["materialized_realization_id"]
        )
        narrowed = call(
            server,
            "/api/query",
            {
                "token": selected["token"],
                "query": {"parameters": [{"key": "loop_nt", "values": [100]}]},
            },
        )
        assert narrowed["selection"] is None and narrowed["preview_status"] == "excluded_by_query"
        with pytest.raises(HTTPError):
            call(
                server,
                "/api/retrieve",
                {"token": narrowed["token"], "selection": selected["selection"]},
            )
        restored = call(server, "/api/query", {"token": narrowed["token"], "query": {}})
        assert restored["selection"] == selected["selection"]
        with pytest.raises(HTTPError):
            call(server, "/api/evaluate", {"token": restored["token"]})
        assert restored["preview"]["drawing"] is None
        route = call(
            server,
            "/api/view",
            {
                "token": restored["token"],
                "stage": "all",
                "camera": None,
                "presentation": {**restored["presentation"], "molecule": "route"},
            },
        )
        assert route["selection"] == selected["selection"]
        assert call(server, route["preview"]["drawing"])
    finally:
        server.shutdown()
        server.server_close()
        session.close()
        thread.join(timeout=5)


def test_failed_preview_keeps_last_coherent_inspection(captured_edition, tmp_path, monkeypatch):  # noqa: F811
    session = DesignInspectionSession(captured_edition, tmp_path / "view")
    try:
        selected = session.sample({"token": session.state()["token"], "seed": 0})

        def fail(*args, **kwargs):
            raise ValueError("preview failed")

        monkeypatch.setattr(session._cache, "get", fail)
        with pytest.raises(ValueError, match="preview failed"):
            session.query({"token": selected["token"], "query": {}})
        after = session.state()
        assert after == selected
    finally:
        session.close()


def test_http_reuses_only_the_clients_matching_cohort(captured_edition, tmp_path):  # noqa: F811
    session = DesignInspectionSession(captured_edition, tmp_path / "view")
    server = EditorServer(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        initial = call(server, "/api/state")
        selected = call(
            server, "/api/sample", {"token": initial["token"], "seed": 0}, cohort=initial["cohort"]
        )
        assert selected["cohort_unchanged"] is True
        assert "feature_parameters" not in selected
        assert "choices" not in selected and "families" not in selected
        assert selected["cohort"] == initial["cohort"]
        full = call(server, "/api/state")
        assert {**initial, **selected, "cohort_unchanged": False} == full
        # The hint is not authority: incorrect hints receive the full answer;
        # a matching hint cannot bypass the action token or filter semantics.
        wrong = call(server, "/api/state", cohort="wrong")
        assert wrong == full
        with pytest.raises(HTTPError) as error:
            call(
                server,
                "/api/sample",
                {"token": initial["token"], "seed": 1},
                cohort=initial["cohort"],
            )
        assert error.value.code == 400
        filtered = call(
            server,
            "/api/query",
            {
                "token": selected["token"],
                "query": {"parameters": [{"key": "loop_nt", "values": [100]}]},
            },
            cohort=selected["cohort"],
        )
        assert filtered["cohort_unchanged"] is False
        assert filtered["cohort"] != selected["cohort"]
        assert filtered["choices"]["matching_preparations"] == 0
        assert filtered["feature_parameters"] == captured_edition.parameters(
            query={"parameters": [{"key": "loop_nt", "values": [100]}]}
        )
        assert "families" in filtered
    finally:
        server.shutdown()
        server.server_close()
        session.close()
        thread.join(timeout=5)


def test_completed_discovery_opens_real_inspector_on_same_server(
    captured_choices,  # noqa: F811
    captured_edition,  # noqa: F811
    tmp_path,
    monkeypatch,
):
    from hop_design import construction

    session = DesignInspectionSession(captured_edition, tmp_path / "view")
    selected = session.sample({"token": session.state()["token"], "seed": 0})
    controller = session._discovery
    controller._job = {
        "id": "completed",
        "status": "completed",
        "matching_preparations": 1,
        "directory": str(captured_choices._directory),
        "can_continue": True,
    }

    def no_search(*args, **kwargs):
        pytest.fail("Inspection must not discover new preparations or fit coordinates")

    monkeypatch.setattr(construction, "discover_designs", no_search)
    monkeypatch.setattr(construction, "continue_design_discovery", no_search)
    server = EditorServer(session, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        opened = call(
            server,
            "/api/inspect-discovery",
            {"token": selected["token"], "job_id": "completed"},
            cohort=selected["cohort"],
        )
        assert server.session is not session
        assert server.session._discovery is controller
        assert opened["cohort_unchanged"] is False
        assert (
            opened["selection"]["materialized_realization_id"]
            == selected["selection"]["materialized_realization_id"]
        )
        assert opened["has_landscape"] is False
        assert opened["presentation"]["landscape"] == "families"
        assert call(server, opened["preview"]["teaching"])
        assert call(server, opened["plots"]["inspection"])
        assert call(server, "/api/state")["selection"] == opened["selection"]
        assert not session.cache_root.exists()
        assert controller.snapshot("completed")["can_continue"] is True
    finally:
        server.shutdown()
        server.server_close()
        server.session.close()
        thread.join(timeout=5)
    assert not thread.is_alive()
