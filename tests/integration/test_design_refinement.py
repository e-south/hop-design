"""Displayed molecular vocabulary survives the complete public choice lifecycle."""

import json

import pytest

from hop_design import construction
from tests.integration.test_design_discovery import intent_document


@pytest.fixture(scope="module")
def choices(tmp_path_factory):
    return construction.discover_designs(
        intent_document(), tmp_path_factory.mktemp("refinement") / "designs", max_evaluations=1
    )


def test_method_name_and_identity_have_the_same_query_selection_and_figure(choices):
    named = {"parameters": [{"key": "release_method", "values": ["BsaI-HFv2"]}]}
    identified = {
        "parameters": [{"key": "release_method", "values": ["example:enzyme/bsai-hfv2@1"]}]
    }
    expected = choices.query(identified)
    actual = choices.query(named)
    assert actual["matching_preparations"] == expected["matching_preparations"] > 0
    assert actual["query"] == expected["query"]
    assert actual["submitted_query"]["parameters"][0]["values"] == ["BsaI-HFv2"]
    selected = choices.sample(seed=1, query=named)
    assert selected == choices.sample(seed=1, query=identified)
    assert choices.select(selected["materialized_realization_id"], query=named) == selected
    assert choices.figure(query=named, selection=selected).json_bytes
    assert choices.explain(named) == choices.explain(identified)


def test_contradictory_equivalent_measurements_fail_before_filtering(choices):
    query = {
        "parameters": [
            {"key": "foldback_arm_bp", "values": [6]},
            {"key": "loop_side_paired_bp", "minimum": 7, "maximum": 8},
        ]
    }
    before = choices.query()
    with pytest.raises(ValueError, match=r"foldback_arm_bp.*loop_side_paired_bp.*conflict"):
        choices.explain(query)
    assert choices.query() == before


def test_compatible_equivalent_measurements_preserve_existing_selection_queries(choices):
    query = {
        "parameters": [
            {"key": "foldback_arm_bp", "values": [6, 7]},
            {"key": "loop_side_paired_bp", "minimum": 5, "maximum": 6},
        ]
    }
    result = choices.query(query)
    assert result["matching_preparations"] > 0
    assert result["query"]["parameters"] == [
        {**p, **({"minimum": None, "maximum": None} if "values" in p else {"values": None})}
        for p in query["parameters"]
    ]
    assert all(p["values"]["foldback_arm_bp"] == 6 for p in result["paths"] if p["matches"])


def test_unknown_method_is_explained_instead_of_an_empty_pool(choices):
    with pytest.raises(ValueError, match=r"release.*not permitted.*Permitted methods"):
        choices.query({"parameters": [{"key": "release_method", "values": ["not-an-enzyme"]}]})


def test_insert_preservation_uses_the_same_lifecycle(choices):
    query = choices.preserve(choices.sample(seed=0), stage="endpoint", except_neighborhood="loop")
    assert choices.query(query)["matching_preparations"] > 0
    comparison = choices.compare(
        {
            "stage": "endpoint",
            "required_members": [{"name": "loop", "loop_sequence": "GAAA"}],
            "max_group_evaluations": 8,
        }
    )
    assert comparison["comparison_stage"] == "endpoint"


def test_cli_and_browser_resolve_names_identically(choices, tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app
    from hop_design.commands.design.browser import create_design_server

    query = {"parameters": [{"key": "release_method", "values": ["BsaI-HFv2"]}]}
    path = tmp_path / "query.json"
    path.write_text(json.dumps(query))
    cli = CliRunner().invoke(
        app, ["design", "query", str(choices._directory), "--query", str(path), "--format", "json"]
    )
    assert cli.exit_code == 0, cli.output
    assert json.loads(cli.output) == choices.query(query)
    server = create_design_server(choices._directory, tmp_path / "view")
    try:
        state = server.session.state()
        result = server.session.query({"token": state["token"], "query": query})
        assert result["explanation"] == choices.explain(query)
        assert result["choices"]["query"]["parameters"][0]["values"] == [
            "example:enzyme/bsai-hfv2@1"
        ]
    finally:
        server.server_close()
        server.session.close()


def test_browser_commands_execute_from_a_nondefault_location(choices, tmp_path, monkeypatch):
    import shlex
    import shutil

    from typer.testing import CliRunner

    from hop_design.cli import app
    from hop_design.commands.design.browser import create_design_server

    root = tmp_path / "my designs' copy"
    shutil.copytree(choices._directory, root)
    server = create_design_server(root, tmp_path / "browser view")
    monkeypatch.chdir(tmp_path)
    try:
        state = server.session.state()
        state = server.session.sample({"token": state["token"], "seed": 1})
        assert str(root) in state["command_context"]["directory"]
        commands = state["commands"].splitlines()
        runner = CliRunner()
        executed = []
        for line in commands:
            if line.startswith("#") or not line:
                continue
            arguments = shlex.split(line)
            if arguments[2] in {"sample", "continue"}:
                continue
            result = runner.invoke(app, arguments[1:])
            assert result.exit_code == 0, result.output
            executed.append(arguments[2])
        assert executed == ["query", "select", "atlas", "retrieve"]
        selected = json.loads((tmp_path / "selection.json").read_bytes())
        assert selected == state["selection"]
    finally:
        server.server_close()
        server.session.close()


def test_browser_exclusion_commands_never_offer_unchanged_continuation(tmp_path):
    from hop_design.commands.design.browser import create_design_server

    root = tmp_path / "excluded designs"
    construction.discover_designs(
        {
            "stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT",
            "product": "released_insert",
            "ends": {"left": "AGTC", "right": "AACC"},
        },
        root,
        max_evaluations=64,
    )
    server = create_design_server(root, tmp_path / "view")
    try:
        state = server.session.state()
        assert state["explanation"]["status"] == "excluded_within_scope"
        assert "design continue" not in state["commands"]
        assert "design sample" not in state["commands"]
    finally:
        server.server_close()
        server.session.close()
