"""An explicit envelope jump retains its original evidence and exact query intention."""

import json
import shutil

import pytest

from hop_design import construction


def test_new_loop_outside_original_permissions_is_previewed_evaluated_and_retrieved(
    loop_pool, tmp_path
):
    before = json.loads(loop_pool.json_bytes)
    reference = before["options"][0]["label"]
    query = {
        "schema": "hop.scaffold-variant-query/v2",
        "result_digest": loop_pool.result_digest,
        "stage": "hairpin",
        "focus": "loop",
        "reference": reference,
        "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
        "parameters": [{"key": "loop_word", "values": ["AAAA"]}],
    }
    choices = construction.query_scaffold_variants(loop_pool, query)
    assert not json.loads(choices.json_bytes)["compatible_options"]
    revision = {
        "schema": "hop.scaffold-envelope-revision/v1",
        "changes": [
            {"path": "product.foldback.geometry.loop_sequences", "value": None},
        ],
    }
    preview = construction.preview_scaffold_envelope_revision(loop_pool, choices, revision)
    summary = json.loads(preview.json_bytes)
    assert summary["status"] == "ready"
    assert summary["changes"][0]["before"] == ["GAAA", "TTTC"]
    assert summary["changes"][0]["after"] is None
    assert summary["query"]["reference"] == reference
    assert summary["query"]["controls"] == query["controls"]
    assert json.loads(loop_pool.json_bytes) == before
    saved = preview.write(tmp_path / "preview")
    loaded = construction.load_scaffold_envelope_revision(loop_pool, saved)
    assert loaded.json_bytes == preview.json_bytes
    packet = construction.evaluate_scaffold_envelope_revision(
        loop_pool, loaded, max_branches=1, max_continuations_per_branch=1
    )
    path = packet.write(tmp_path / "evaluated")
    shutil.copytree(path, tmp_path / "relocated")
    expanded = construction.load_scaffold_exploration(tmp_path / "relocated")
    observations = json.loads(expanded.json_bytes)
    assert observations["options"][: len(before["options"])] == before["options"]
    assert observations["parameter_domains"]["loop_word"]["basis"] == "unfixed_sequence_domain"
    query["result_digest"] = expanded.result_digest
    refreshed = construction.query_scaffold_variants(expanded, query)
    facts = json.loads(refreshed.json_bytes)
    assert facts["query"]["controls"] == query["controls"]
    assert facts["compatible_options"]
    label = facts["compatible_options"][0]
    assert (
        next(o for o in observations["options"] if o["label"] == label)["loop_sequence"] == "AAAA"
    )
    selected = construction.select_scaffold_variants(
        tmp_path / "relocated", refreshed, members={"new_loop": label}, baseline="new_loop"
    )
    assert selected.json_bytes
    # The revised pool can subsequently target another word, without the old shortlist.
    query["parameters"] = [{"key": "loop_word", "values": ["AAAT"]}]
    next_choices = construction.query_scaffold_variants(expanded, query)
    from hop_design.design.construction.variants.parameter_evaluation import evaluation_request

    target = evaluation_request(expanded, next_choices, 1, 1)
    assert target["product"]["foldback"]["geometry"].get("loop_sequences") is None


def test_revision_preview_keeps_conflicting_selected_value_without_relaxing_it(loop_pool):
    query = {
        "schema": "hop.scaffold-variant-query/v2",
        "result_digest": loop_pool.result_digest,
        "stage": "hairpin",
        "focus": "loop",
        "parameters": [{"key": "loop_word", "values": ["AAAA"]}],
    }
    choices = construction.query_scaffold_variants(loop_pool, query)
    preview = construction.preview_scaffold_envelope_revision(
        loop_pool,
        choices,
        {
            "schema": "hop.scaffold-envelope-revision/v1",
            "changes": [{"path": "product.foldback.geometry.loop_sequences", "value": ["CCCC"]}],
        },
    )
    assert json.loads(preview.json_bytes)["status"] == "conflicting_requirements"
    with pytest.raises(ValueError, match="conflict"):
        construction.evaluate_scaffold_envelope_revision(
            loop_pool, preview, max_branches=1, max_continuations_per_branch=1
        )


def test_cli_previews_the_same_explicit_revision(loop_options, tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app

    pool = construction.load_scaffold_exploration(loop_options[0])
    choices = construction.query_scaffold_variants(
        pool,
        {
            "schema": "hop.scaffold-variant-query/v2",
            "result_digest": pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
            "parameters": [{"key": "loop_word", "values": ["AAAA"]}],
        },
    )
    choices.write(tmp_path / "choices")
    value = {
        "schema": "hop.scaffold-envelope-revision/v1",
        "changes": [
            {"path": "product.foldback.geometry.loop_sequences", "value": None},
        ],
    }
    source = tmp_path / "revision.json"
    source.write_text(json.dumps(value))
    expected = construction.preview_scaffold_envelope_revision(pool, choices, source)
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "revise-envelope",
            str(loop_options[0]),
            str(tmp_path / "choices"),
            str(source),
            "--out",
            str(tmp_path / "preview"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "preview/summary.json").read_bytes() == expected.json_bytes


def test_browser_revision_is_bound_to_the_current_query(loop_options, tmp_path):
    from hop_design.commands.construction.editor.variants import VariantSession

    session = VariantSession(loop_options[0], tmp_path / "session")
    state = session.state()
    assert state["pool"]["envelope"]["fields"]
    domain = session.parameter_domain(
        {
            "query_digest": state["choices"]["query_digest"],
            "request": {"key": "loop_word"},
        }
    )
    assert {entry["value"] for entry in domain["values"]} == {"GAAA", "TTTC"}
    assert session.state() == state
    payload = {
        "query_digest": state["choices"]["query_digest"],
        "revision": {
            "schema": "hop.scaffold-envelope-revision/v1",
            "changes": [
                {"path": "product.foldback.geometry.loop_sequences", "value": None},
            ],
        },
    }
    revised = session.preview_envelope(payload)
    assert revised["envelope_revision"]["status"] == "ready"
    assert revised["pool"] == state["pool"]
    state["choices"]["query"]["schema"] = "hop.scaffold-variant-query/v2"
    state["choices"]["query"]["parameters"] = [{"key": "loop_word", "values": ["AAAA"]}]
    session.query(state["choices"]["query"])
    with pytest.raises(ValueError, match="Stale"):
        session.preview_envelope(payload)
    with pytest.raises(ValueError, match="preview"):
        session.evaluate_envelope(
            {
                "query_digest": session.state()["choices"]["query_digest"],
                "revision_digest": revised["envelope_revision"]["revision_digest"],
                "max_branches": 1,
                "max_continuations_per_branch": 1,
            }
        )


def test_domain_values_explain_existing_witnesses_blocked_by_another_selection(loop_pool):
    choices = construction.query_scaffold_variants(
        loop_pool,
        {
            "schema": "hop.scaffold-variant-query/v2",
            "result_digest": loop_pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
            "parameters": [{"key": "self_paired_arm_bp", "values": [900]}],
        },
    )
    page = construction.query_scaffold_parameter_domain(loop_pool, choices, {"key": "loop_word"})
    result = json.loads(page.json_bytes)
    assert result["total"] == "2"
    assert {v["value"] for v in result["values"]} == {"GAAA", "TTTC"}
    assert all(v["status"] == "blocked_by_selections" for v in result["values"])
    assert all(v["complete_preparations"] > 0 for v in result["values"])
    assert all(v["matching_preparations"] == 0 for v in result["values"])
    for value in result["values"]:
        assert all(
            "self_paired_arm_bp" in candidate["different_selections"]
            for candidate in value["recorded_alternatives"]
        )


def test_preview_names_inherited_parameter_conflict_without_clearing_query(loop_pool):
    choices = construction.query_scaffold_variants(
        loop_pool,
        {
            "schema": "hop.scaffold-variant-query/v2",
            "result_digest": loop_pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
            "parameters": [{"key": "loop_word", "values": ["GAAA"]}],
        },
    )
    preview = construction.preview_scaffold_envelope_revision(
        loop_pool,
        choices,
        {
            "schema": "hop.scaffold-envelope-revision/v1",
            "changes": [
                {"path": "parameters", "value": [{"key": "loop_word", "values": ["TTTC"]}]}
            ],
        },
    )
    facts = json.loads(preview.json_bytes)
    assert facts["status"] == "conflicting_requirements"
    assert facts["query"] == json.loads(choices.json_bytes)["query"]
    assert facts["conflicts"][0]["requested_field"] == "parameters.loop_word"
    assert "inherited" in facts["conflicts"][0]["explicit_edit"]


def test_preview_rejects_modified_derived_request_even_with_resealed_manifest(loop_pool, tmp_path):
    from hop_design.serialization import canonical_json_bytes, sha256_digest

    choices = construction.query_scaffold_variants(
        loop_pool, {"result_digest": loop_pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    preview = construction.preview_scaffold_envelope_revision(
        loop_pool,
        choices,
        {
            "schema": "hop.scaffold-envelope-revision/v1",
            "changes": [{"path": "product.foldback.geometry.loop_sequences", "value": None}],
        },
    )
    saved = preview.write(tmp_path / "preview")
    target = saved / "envelope-request.json"
    value = json.loads(target.read_bytes())
    value["product"]["stem_arm"] = "AAAA"
    target.write_bytes(canonical_json_bytes(value))
    manifest = json.loads((saved / "manifest.json").read_bytes())
    manifest["artifacts"]["envelope-request.json"] = sha256_digest(target.read_bytes())
    (saved / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ValueError):
        construction.load_scaffold_envelope_revision(loop_pool, saved)


def test_http_domain_revision_evaluation_and_retrieval_use_the_same_controls(
    loop_options, tmp_path
):
    import threading
    from urllib.error import HTTPError

    from hop_design.commands.construction.editor.server import create_editor_server
    from tests.integration.test_molecular_editor_http import call

    server = create_editor_server(loop_options[0], tmp_path / "viewer", evaluated=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for name in ("envelope_browser.js", "envelope_model.js", "envelope_fields.js"):
            assert call(server, "/" + name)
        state = call(server, "/api/state")
        original = state["pool"]["result_digest"]
        query = {
            **state["choices"]["query"],
            "schema": "hop.scaffold-variant-query/v2",
            "reference": state["choices"]["compatible_options"][0],
            "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
            "parameters": [{"key": "loop_word", "values": ["AAAA"]}],
        }
        state = call(server, "/api/query", query)
        assert not state["choices"]["compatible_options"]
        revision = {
            "query_digest": state["choices"]["query_digest"],
            "revision": {
                "schema": "hop.scaffold-envelope-revision/v1",
                "changes": [{"path": "product.foldback.geometry.loop_sequences", "value": None}],
            },
        }
        preview = call(server, "/api/preview-envelope", revision)
        assert preview["pool"]["result_digest"] == original
        state = call(
            server,
            "/api/evaluate-envelope",
            {
                "query_digest": preview["choices"]["query_digest"],
                "revision_digest": preview["envelope_revision"]["revision_digest"],
                "max_branches": 1,
                "max_continuations_per_branch": 1,
            },
        )
        assert state["pool"]["result_digest"] != original
        assert state["choices"]["query"]["controls"] == query["controls"]
        assert state["choices"]["query"]["reference"] == query["reference"]
        assert state["choices"]["compatible_options"]
        domain = call(
            server,
            "/api/parameter-domain",
            {
                "query_digest": state["choices"]["query_digest"],
                "request": {"key": "loop_word", "length": 4, "prefix": "AAA"},
            },
        )
        assert domain["total"] == "4"
        assert [v["value"] for v in domain["values"]] == ["AAAA", "AAAC", "AAAG", "AAAT"]
        selected = call(
            server,
            "/api/select",
            {
                "query_digest": state["choices"]["query_digest"],
                "members": {"new_loop": state["choices"]["compatible_options"][0]},
                "baseline": "new_loop",
            },
        )
        assert call(server, selected["selection"]["archive"]).startswith(b"PK")
        with pytest.raises(HTTPError):
            call(server, "/api/preview-envelope", revision)
    finally:
        server.shutdown()
        server.server_close()
        server.session.close()
        thread.join(timeout=5)
