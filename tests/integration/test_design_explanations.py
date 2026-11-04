"""Molecular answers preserve the existing exact-choice lifecycle."""

import pytest

from hop_design import construction
from tests.integration.test_design_discovery import intent_document


def test_first_answer_identifies_available_molecules_without_selecting_one(tmp_path):
    choices = construction.discover_designs(
        intent_document(), tmp_path / "designs", max_evaluations=1
    )
    before = choices.query()
    answer = choices.explain()
    assert answer["status"] == "choices_available"
    assert answer["product"] == "released_insert"
    assert answer["matching_preparations"] == before["matching_preparations"]
    assert answer["choices"][0]["values"]["left_end_word"] == "AAAA"
    assert answer["choices"][0]["values"]["right_end_word"] == "AAAA"
    assert answer["choices"][0]["materialized_realization_id"] in {
        p["materialized_realization_id"] for p in before["paths"]
    }
    assert "select" in answer["actions"]
    assert "selection" not in answer
    assert choices.query() == before


def test_hairpin_query_rejects_release_coordinates_even_with_no_complete_options(tmp_path):
    choices = construction.discover_designs(
        {"stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT", "product": "hairpin"},
        tmp_path / "hairpins",
        max_evaluations=1,
        effort={"local_nodes": 64, "local_realizations": 1, "release_site_pairs": 1},
    )
    for key, value in (("left_end_word", "AAAA"), ("release_method", "BsaI-HFv2")):
        with pytest.raises(ValueError, match=r"not applicable.*hairpin.*released insert"):
            choices.query({"parameters": [{"key": key, "values": [value]}]})
    # Source-copying and foldback measurements remain meaningful on the route.
    choices.query({"parameters": [{"key": "source_reverse_primer_required_nt", "values": [14]}]})
    assert choices.explain()["parameters"]
    release = next(p for p in choices.explain()["parameters"] if p["key"] == "left_end_word")
    assert release["applicable"] is False


def test_excluded_request_does_not_offer_unchanged_search(tmp_path):
    choices = construction.discover_designs(
        {
            "stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT",
            "product": "released_insert",
            "ends": {"left": "AGTC", "right": "AACC"},
        },
        tmp_path / "excluded",
        max_evaluations=64,
    )
    assert choices.query()["coverage"]["excluded_pairs"] == 1
    answer = choices.explain()
    assert answer["status"] == "excluded_within_scope"
    assert "continuing unchanged" in answer["guidance"].lower()
    assert "continue_search" not in answer["actions"]
    assert "revise_request" in answer["actions"]
    assert "context" in answer["headline"]


def test_unrecorded_filter_retains_uncertainty_and_explicit_next_actions(tmp_path):
    choices = construction.discover_designs(
        intent_document(), tmp_path / "designs", max_evaluations=1
    )
    query = {"parameters": [{"key": "left_end_word", "values": ["TGCA"]}]}
    answer = choices.explain(query)
    assert answer["status"] == "no_recorded_match"
    assert "continue_search" in answer["actions"]
    assert "refine_query" in answer["actions"]
    assert not answer["choices"]
    assert answer["coverage"]["unresolved_pairs"] > 0


def test_search_is_not_recommended_for_values_outside_saved_permissions(tmp_path):
    choices = construction.discover_designs(
        intent_document(), tmp_path / "designs", max_evaluations=1
    )
    answer = choices.explain({"parameters": [{"key": "loop_nt", "values": [99]}]})
    assert answer["status"] == "no_recorded_match"
    assert "continue_search" not in answer["actions"]
    assert "inspect_permissions" in answer["actions"]


def test_readable_cli_and_explicit_json_share_the_same_choices(tmp_path):
    import json

    from typer.testing import CliRunner

    from hop_design.cli import app

    directory = tmp_path / "designs"
    choices = construction.discover_designs(intent_document(), directory, max_evaluations=1)
    runner = CliRunner()
    text_result = runner.invoke(app, ["design", "query", str(directory), "--format", "text"])
    assert text_result.exit_code == 0, text_result.output
    assert choices.explain()["headline"] in text_result.output
    assert "AAAA" in text_result.output
    assert "hop-design design view" in text_result.output
    assert len(text_result.output) < 2500
    json_result = runner.invoke(app, ["design", "query", str(directory), "--format", "json"])
    assert json_result.exit_code == 0, json_result.output
    assert json.loads(json_result.output) == choices.query()
    default_result = runner.invoke(app, ["design", "query", str(directory)])
    assert json.loads(default_result.output) == choices.query()


def test_browser_explanation_matches_api_after_filtering(tmp_path):
    from hop_design.commands.design.browser import create_design_server

    directory = tmp_path / "designs"
    choices = construction.discover_designs(intent_document(), directory, max_evaluations=1)
    server = create_design_server(directory, tmp_path / "browser")
    try:
        state = server.session.state()
        assert state["explanation"] == choices.explain()
        query = {"parameters": [{"key": "left_end_word", "values": ["TGCA"]}]}
        state = server.session.query({"token": state["token"], "query": query})
        assert state["explanation"] == choices.explain(query)
        assert state["selection"] is None
    finally:
        server.server_close()
        server.session.close()


def test_hairpin_browser_explains_empty_pool_and_rejects_inapplicable_filter(tmp_path):
    from hop_design.commands.design.browser import create_design_server

    root = tmp_path / "hairpins"
    choices = construction.discover_designs(
        {"stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT", "product": "hairpin"},
        root,
        max_evaluations=1,
        effort={"local_nodes": 64, "local_realizations": 1, "release_site_pairs": 1},
    )
    server = create_design_server(root, tmp_path / "browser")
    try:
        state = server.session.state()
        assert state["explanation"]["headline"] == choices.explain()["headline"]
        assert state["explanation"]["matching_preparations"] == 0
        for key, value in (("left_end_word", "AAAA"), ("left_gap", 0)):
            request = {
                **state["choices"]["query"],
                "parameters": [{"key": key, "values": [value]}],
            }
            with pytest.raises(ValueError, match="not applicable"):
                server.session.query({"token": state["token"], "query": request})
            assert server.session.state()["choices"] == state["choices"]
    finally:
        server.server_close()
        server.session.close()


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        (
            {"scaffold": {"loop_nt": {"minimum": 99, "maximum": 99}}},
            ("loop_nt", "99", "3", "8", "foldback.geometry"),
        ),
        ({"methods": {"basal": ["Nb.BtsI"]}}, ("Nb.BtsI", "Nb.BsrDI", "basal.enzymes")),
    ],
)
def test_context_conflicts_name_requirement_permissions_and_edit(requirement, expected):
    with pytest.raises(ValueError) as error:
        construction.resolve_design_request(
            {
                "stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT",
                "product": "released_insert",
                **requirement,
            }
        )
    for text in expected:
        assert text in str(error.value)


def test_output_mode_respects_terminal_and_explicit_override(monkeypatch):
    import sys

    from hop_design.commands.design.presentation import OutputFormat, use_text

    for terminal in (True, False):
        monkeypatch.setattr(sys.stdout, "isatty", lambda terminal=terminal: terminal)
        assert use_text(OutputFormat.AUTO) is terminal
        assert use_text(OutputFormat.TEXT) is True
        assert use_text(OutputFormat.JSON) is False


def test_partial_coverage_cannot_override_narrower_proof_or_invent_geometry_exclusion(tmp_path):
    from hop_design.design.construction.variants.explanation import explain_choices

    choices = construction.discover_designs(
        intent_document(), tmp_path / "designs", max_evaluations=1
    )
    result = choices.query({"parameters": [{"key": "left_end_word", "values": ["TGCA"]}]})
    node = next(
        n
        for a in result["axes"]
        if a["key"] == "left_end_word"
        for n in a["nodes"]
        if n["value"] == "TGCA"
    )
    node["state"] = "excluded_in_scope"
    answer = explain_choices(choices.resolution, result)
    assert answer["status"] == "excluded_within_scope"
    assert "continue_search" not in answer["actions"]
    # Completing one witness per end pair does not enumerate every scaffold.
    result["query"]["parameters"] = [{"key": "loop_nt", "values": [99]}]
    result["axes"].append(
        {"key": "loop_nt", "nodes": [{"value": 99, "state": "excluded_in_scope"}]}
    )
    result["fully_enumerated"] = True
    result["all_preparations_enumerated"] = False
    assert explain_choices(choices.resolution, result)["status"] == "no_recorded_match"


@pytest.mark.parametrize(
    "operation,filename", [("figure", "figure.pdf"), ("atlas", "projection.svg")]
)
def test_export_commands_report_the_actual_file(tmp_path, operation, filename):
    import json

    from typer.testing import CliRunner

    from hop_design.cli import app

    root = tmp_path / "designs"
    choices = construction.discover_designs(intent_document(), root, max_evaluations=1)
    selected = tmp_path / "selection.json"
    selected.write_text(json.dumps(choices.sample(seed=1)))
    output = tmp_path / operation
    result = CliRunner().invoke(
        app, ["design", operation, str(root), "--selection", str(selected), "--out", str(output)]
    )
    assert result.exit_code == 0, result.output
    assert str(output / filename) in result.output
    assert (output / filename).is_file()
