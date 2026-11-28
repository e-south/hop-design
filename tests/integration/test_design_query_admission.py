"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_design_query_admission.py

Keep query rejection and explicit saved-view overrides consistent across adapters.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.commands.design.inspection import DesignInspectionSession
from tests.integration.test_design_discovery import intent_document


@pytest.fixture(scope="module")
def choices(tmp_path_factory):
    return construction.discover_designs(
        intent_document(), tmp_path_factory.mktemp("query-admission") / "choices", max_evaluations=1
    )


@pytest.mark.parametrize("query", [False, 0, [], True, 1, [1]])
def test_public_query_rejects_non_mapping_roots_without_changing_choices(choices, query):
    before = choices.query()
    with pytest.raises(ValueError, match="mapping"):
        choices.query(query)
    assert choices.query() == before
    assert choices.query({}) == before


def test_cli_rejects_json_false_while_omission_and_empty_object_agree(choices, tmp_path):
    runner = CliRunner()
    command = ["design", "query", str(choices._directory), "--format", "json"]
    omitted = runner.invoke(app, command)
    assert omitted.exit_code == 0, omitted.output
    source = tmp_path / "query.json"
    source.write_text("{}")
    explicit = runner.invoke(app, [*command, "--query", str(source)])
    assert explicit.exit_code == 0, explicit.output
    assert json.loads(explicit.output) == json.loads(omitted.output)
    source.write_text("false")
    invalid = runner.invoke(app, [*command, "--query", str(source)])
    assert invalid.exit_code == 2
    assert "mapping" in invalid.output


def test_inspection_rejected_query_preserves_active_membership_and_token(choices, tmp_path):
    session = DesignInspectionSession(choices, tmp_path / "inspection")
    try:
        initial = session.state()
        restricted = session.query(
            {
                "token": initial["token"],
                "query": {
                    "membership": {
                        "snapshot_digest": initial["choices"]["snapshot_digest"],
                        "preparations": [],
                    }
                },
            }
        )
        assert restricted["choices"]["matching_preparations"] == 0
        for query in (False, 0, [], True, 1, [1]):
            with pytest.raises(ValueError, match="mapping"):
                session.query({"token": restricted["token"], "query": query})
            assert session.state() == restricted
        cleared = session.query({"token": restricted["token"], "query": {}})
        assert cleared["choices"]["matching_preparations"] > 0
    finally:
        session.close()


def test_saved_view_defaults_only_omitted_query_and_rejects_explicit_mismatch(choices):
    query = {"parameters": [{"key": "left_gap", "values": [6]}]}
    selection = choices.sample(seed=1, query=query)
    view = choices.view(selection)
    omitted = choices.figure(selection=view)
    explicit = choices.figure(selection=view, query=query)
    assert explicit.json_bytes == omitted.json_bytes
    with pytest.raises(ValueError, match="query"):
        choices.figure(selection=selection, query={})
    with pytest.raises(ValueError, match="query"):
        choices.figure(selection=view, query={})
    with pytest.raises(ValueError, match="mapping"):
        choices.figure(selection=view, query=False)
