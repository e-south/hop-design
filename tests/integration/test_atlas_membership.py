"""Family membership is the same restriction in live, captured and command-line use."""

import json

import pytest
from typer.testing import CliRunner

from hop_design.cli import app
from tests.integration.test_atlas_edition import captured_choices, captured_edition  # noqa: F401
from tests.integration.test_design_preservation import loop_designs  # noqa: F401


@pytest.fixture(params=["insert", "hairpin", "edition"])
def choices(request, captured_choices, captured_edition, loop_designs):  # noqa: F811
    return {"insert": captured_choices, "hairpin": loop_designs[1], "edition": captured_edition}[
        request.param
    ]


def test_exact_membership_reopens_and_filters_through_api_cli(choices, tmp_path):
    family = choices.families(stage="hairpin")["families"][0]
    query = family["query"]
    selected_id = family["preparations"][0]
    query = {**query, "membership": {**query["membership"], "preparations": [selected_id]}}
    result = choices.query(query)
    assert result["matching_preparations"] == 1
    assert {p["materialized_realization_id"] for p in result["paths"] if p["matches"]} == {
        selected_id
    }
    selected = choices.select(selected_id, query=query)
    assert selected["query"] == result["query"]
    saved = choices.view(selected)
    assert choices.restore_view(saved) == saved
    assert choices.sample(after=saved)["selection"]["materialized_realization_id"] == selected_id
    source = tmp_path / "query.json"
    source.write_text(json.dumps(query))
    answer = CliRunner().invoke(
        app,
        ["design", "query", str(choices._directory), "--query", str(source), "--format", "json"],
    )
    assert answer.exit_code == 0, answer.output
    assert json.loads(answer.output) == result
    empty = {**query, "membership": {**query["membership"], "preparations": []}}
    assert choices.query(empty)["matching_preparations"] == 0
    assert "continue_search" not in choices.explain(empty)["actions"]
    with pytest.raises(ValueError):
        choices.select(selected_id, query=empty)
    with pytest.raises(ValueError):
        choices.atlas({**selected, "query": empty})
    with pytest.raises(ValueError, match="snapshot"):
        choices.query(
            {
                **query,
                "membership": {**query["membership"], "snapshot_digest": "sha256:" + "0" * 64},
            }
        )


@pytest.mark.parametrize("endpoint", ["insert", "hairpin"])
def test_preservation_and_exact_membership_intersect(
    endpoint,
    captured_choices,  # noqa: F811
    loop_designs,  # noqa: F811
    tmp_path,
):
    choices = captured_choices if endpoint == "insert" else loop_designs[1]
    selected = choices.sample(seed=0)
    preserved = choices.preserve(selected, stage="hairpin", except_neighborhood="loop")
    query = {
        **preserved,
        "membership": {"snapshot_digest": choices.query()["snapshot_digest"], "preparations": []},
    }
    result = choices.query(query)
    assert result["matching_preparations"] == 0
    assert all(n["conditional_preparations"] == 0 for axis in result["axes"] for n in axis["nodes"])
    exact = {
        **query,
        "membership": {
            **query["membership"],
            "preparations": [selected["materialized_realization_id"]],
        },
    }
    chosen = choices.select(selected["materialized_realization_id"], query=exact)
    assert choices.atlas(chosen).json_bytes
    assert choices.retrieve(
        chosen, tmp_path / "controlled-materials"
    ).materialized_realization_ids == (selected["materialized_realization_id"],)


def test_saved_figure_cannot_display_a_different_query_than_its_selection(captured_choices):  # noqa: F811
    selected = captured_choices.sample(seed=0)
    view = captured_choices.view(selected)
    query = captured_choices.families(stage="hairpin")["families"][0]["query"]
    # This includes the selected preparation, but represents a different query.
    with pytest.raises(ValueError, match="figure query"):
        captured_choices.figure(selection=view, query=query)
