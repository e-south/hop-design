"""The introductory CLI consumes the same optional intent and saved selections as the API."""

import json

from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.integration.test_design_discovery import intent_document


def test_discover_query_sample_and_retrieve_match_the_public_api(tmp_path):
    runner = CliRunner()
    intent = tmp_path / "intent.json"
    intent.write_text(json.dumps(intent_document()))
    output = tmp_path / "designs"
    executed = runner.invoke(
        app,
        [
            "design",
            "discover",
            "--request",
            str(intent),
            "--out",
            str(output),
            "--evaluations",
            "1",
        ],
    )
    assert executed.exit_code == 0, executed.output
    api = construction.load_design_choices(output)
    query = runner.invoke(app, ["design", "query", str(output)])
    assert query.exit_code == 0, query.output
    assert json.loads(query.output) == api.query()
    selection = tmp_path / "selection.json"
    sampled = runner.invoke(
        app, ["design", "sample", str(output), "--seed", "1", "--out", str(selection)]
    )
    assert sampled.exit_code == 0, sampled.output
    assert json.loads(selection.read_text()) == api.sample(seed=1)
    retrieved = runner.invoke(
        app,
        [
            "design",
            "retrieve",
            str(output),
            "--selection",
            str(selection),
            "--out",
            str(tmp_path / "materials"),
        ],
    )
    assert retrieved.exit_code == 0, retrieved.output
    assert (
        api.sample(seed=1)["materialized_realization_id"]
        in json.loads(retrieved.output)["witnesses"]
    )


def test_plain_stem_flags_resolve_without_any_end_words(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "design",
            "resolve",
            "--stem",
            "ACGTACGTACGT",
            "--product",
            "released_insert",
            "--out",
            str(tmp_path / "intent"),
        ],
    )
    assert result.exit_code == 0, result.output
    summary = json.loads((tmp_path / "intent/summary.json").read_bytes())
    assert summary["intent"]["ends"] is None
    assert summary["effective_request"]["targets"] == {"left_words": None, "right_words": None}


def test_browser_opens_the_same_discovery_and_exposes_effective_intent(tmp_path):
    import importlib

    from hop_design.api import _InspectionProjection

    choices = construction.discover_designs(
        intent_document(), tmp_path / "designs", max_evaluations=1
    )
    browser = importlib.import_module("hop_design.commands.design")
    server = browser.create_design_server(tmp_path / "designs", tmp_path / "browser", port=0)
    try:
        state = server.session.state()
        assert state["discovery"] == choices.resolution
        assert state["choices"] == _InspectionProjection.display(choices.query())
        picked = server.session.sample({"token": state["token"], "seed": 1})
        assert picked["selection"] == choices.sample(seed=1)
    finally:
        server.server_close()
        server.session.close()
