"""The single-molecule viewer consumes public conditional choices, not a second solver."""

import threading
from pathlib import Path

import pytest

from hop_design.commands.construction.editor.server import create_editor_server
from tests.integration.test_molecular_editor_http import call


def test_variant_view_queries_existing_options_and_retrieves_only_active_choices(
    loop_options, tmp_path
):
    path, _ = loop_options
    server = create_editor_server(path, tmp_path / "viewer", evaluated=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        page = call(server, "/")
        assert b"Explore a complete preparation" in page
        assert b'id="choice-space"' in page
        for asset in Path("src/hop_design/assets/variant_explorer").glob("*.js"):
            assert call(server, "/" + asset.name)
        assert b"textarea" not in page
        state = call(server, "/api/state")
        assert state["selection"] is None
        assert len(state["choices"]["products"]) == 2
        space = state["choices"]["choice_space"]
        assert len(space["products"]) == 2
        assert [p["option_label"] for p in space["paths"]] == state["choices"]["compatible_options"]
        initial_choices = state["choices"]
        local = initial_choices["variants"][1]
        browsed = call(
            server,
            "/api/browse",
            {
                "result_digest": state["pool"]["result_digest"],
                "query_digest": initial_choices["query_digest"],
                "variant_id": local["variant_id"],
                "state": "cleaved_duplex",
            },
        )
        assert browsed["choices"] == initial_choices
        assert browsed["preview"]["option_label"] == local["option_labels"][0]
        assert browsed["preview"]["molecular_state"]["state"]["phase"] == "cleaved_duplex"
        assert browsed["selection"] is None
        teaching = call(server, browsed["preview"]["teaching_drawing"])
        assert teaching.count(b'data-teaching-frame="hairpin"') == 1
        assert b'data-teaching-composition="single-hairpin"' in teaching
        assert b"data-operation-id" in call(server, browsed["preview"]["drawing"])
        first = state["choices"]["compatible_options"][0]
        request = state["choices"]["query"]
        request.update(
            reference=first, controls=[{"stage": "hairpin", "property": "non_loop_sequences"}]
        )
        state = call(server, "/api/query", request)
        assert state["choices"]["query"]["reference"] == first
        assert state["preview"]["option_label"] == local["option_labels"][0]
        state = call(
            server,
            "/api/view",
            {"query_digest": state["choices"]["query_digest"], "option_label": first},
        )
        assert state["preview"]["option_label"] == first
        assert state["selection"] is None
        assert b"<svg" in call(server, state["preview"]["drawing"])
        from urllib.error import HTTPError

        with pytest.raises(HTTPError) as error:
            call(
                server,
                "/api/select",
                {"query_digest": "stale", "members": {"a": first}, "baseline": "a"},
            )
        assert error.value.code == 400
        state = call(
            server,
            "/api/select",
            {
                "query_digest": state["choices"]["query_digest"],
                "members": {"a": first},
                "baseline": "a",
            },
        )
        assert state["selection"]["members"] == ["a"]
        assert call(server, state["selection"]["archive"]).startswith(b"PK")
        selected = state["selection"]
        choices = state["choices"]
        for molecular_state in ("endpoint", "hairpin"):
            state = call(
                server,
                "/api/inspect",
                {
                    "result_digest": state["pool"]["result_digest"],
                    "query_digest": choices["query_digest"],
                    "option_label": first,
                    "state": molecular_state,
                },
            )
            assert state["choices"] == choices
            assert state["selection"] == selected
            assert state["preview"]["inspection"]["state"] == molecular_state
            assert b"data-neighborhood=" in call(server, state["preview"]["drawing"])
            assert b'data-teaching-composition="single-hairpin"' in call(
                server, state["preview"]["teaching_drawing"]
            )
        state = call(
            server,
            "/api/compare",
            {
                "result_digest": state["pool"]["result_digest"],
                "query_digest": choices["query_digest"],
                "required_members": [
                    {"name": "a", "loop_sequence": "GAAA"},
                    {"name": "b", "loop_sequence": "TTTC"},
                ],
                "max_group_evaluations": 32,
                "stage_controls": [
                    {"stage": "hairpin", "property": "non_loop_sequences", "scope": "set"}
                ],
            },
        )
        assert len(state["comparison"]["sets"]) == 1
        state = call(
            server,
            "/api/select-comparison",
            {
                "query_digest": choices["query_digest"],
                "request_digest": state["comparison"]["request_digest"],
                "set_label": "set-0001",
                "baseline": "a",
            },
        )
        assert state["selection"]["members"] == ["a", "b"]
        old_preview = state["preview"]
        other = next(v for v in choices["variants"] if first not in v["option_labels"])
        state = call(
            server,
            "/api/query",
            {
                **choices["query"],
                "pins": [{"neighborhood": "loop", "variant_ids": [other["variant_id"]]}],
            },
        )
        assert state["preview"] == old_preview
        assert state["preview_status"]["status"] == "excluded_by_query"
        assert state["preview_status"]["reasons"]
    finally:
        server.shutdown()
        server.server_close()
        server.session.close()
        thread.join(timeout=5)


def test_inspection_cache_eviction_preserves_receipts_and_query_identity(
    loop_options, tmp_path, monkeypatch
):
    from hop_design.commands.construction.editor.variants import VariantSession

    monkeypatch.setattr(VariantSession, "_cache_limit", 1)
    session = VariantSession(loop_options[0], tmp_path / "bounded-viewer")
    state = session.state()
    request = {
        "result_digest": session.pool.result_digest,
        "query_digest": state["choices"]["query_digest"],
        "option_label": state["choices"]["compatible_options"][0],
        "state": "hairpin",
    }
    first = session.inspect(request)["preview"]
    session.inspect({**request, "state": "endpoint"})
    repeated = session.inspect(request)["preview"]
    assert len(session._inspections) == 1
    assert first["drawing"] != repeated["drawing"]
    assert first["molecular_state"] == repeated["molecular_state"]
    for receipt in (first, repeated):
        assert (session.root / receipt["drawing"].removeprefix("/files/")).is_file()
    session.query({**state["choices"]["query"], "reference": request["option_label"]})
    with pytest.raises(ValueError, match="Stale"):
        session.inspect(request)
