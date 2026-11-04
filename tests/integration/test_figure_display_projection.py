"""Curated figure axes never curate molecular membership or selection."""

import json
from xml.etree import ElementTree as ET

import pytest
from typer.testing import CliRunner

from hop_design.cli import app
from hop_design.commands.design.inspection import DesignInspectionSession
from tests.integration.test_atlas_edition import captured_choices as captured_choices


@pytest.mark.parametrize("kind", ["live", "compact", "captured"])
def test_figure_axis_selection_is_shared_by_cli_and_api(captured_choices, tmp_path, kind):
    choices = captured_choices
    if kind != "live":
        choices = choices.freeze(tmp_path / "edition", compact=kind == "compact")
    selected = choices.sample(seed=1)
    before = choices.query(selected["query"])
    original = dict(choices.figure(selection=selected)._files)
    axes = ("left_gap", "right_gap", "foldback_arm_bp", "loop_nt")
    packet = choices.figure(selection=selected, display_axes=axes)
    exported = dict(packet._files)
    assert exported["choices.json"] == original["choices.json"]
    assert exported["domains.csv"] == original["domains.csv"]
    assert json.loads(exported["choices.json"])["paths"] == before["paths"]
    assert json.loads(exported["selection.json"]) == selected
    receipt = json.loads(exported["display-projection.json"])
    assert receipt["displayed"] == list(axes)
    assert "left_end_word" in receipt["omitted"]
    plot = ET.fromstring(exported["plot.svg"])
    assert [e.get("data-axis") for e in plot.iter() if e.get("data-axis")] == list(axes)
    members = {
        identity
        for e in plot.iter()
        if e.get("data-members")
        for identity in json.loads(e.get("data-members"))
    }
    assert members == {p["materialized_realization_id"] for p in before["paths"]}
    selection_path = tmp_path / "selected.json"
    selection_path.write_text(json.dumps(selected))
    command = [
        "design",
        "figure",
        str(choices._directory),
        "--selection",
        str(selection_path),
        "--out",
        str(tmp_path / "cli"),
    ]
    for axis in axes:
        command.extend(["--axis", axis])
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 0, result.output
    for name in (
        "figure.svg",
        "plot.svg",
        "choices.json",
        "domains.csv",
        "selection.json",
        "display-projection.json",
    ):
        assert (tmp_path / "cli" / name).read_bytes() == exported[name]
    assert choices.query(selected["query"]) == before


@pytest.mark.parametrize("view", ["parameters", "similarity", "families"])
def test_display_projection_preserves_saved_view_and_comparison(captured_choices, tmp_path, view):
    choices = captured_choices.freeze(tmp_path / "edition", compact=True, include_landscape=True)
    selected = choices.sample(seed=2)
    saved = choices.view(selected, render_policy="current", camera=(1, 2, 100, 80))
    axes = ("left_gap", "right_gap")
    packet = choices.figure(
        selection=saved, view=view, display_axes=axes, reference_selection=selected
    )
    files = dict(packet._files)
    assert json.loads(files["display-projection.json"])["displayed"] == list(axes)
    receipt = json.loads(files["view.json"])
    assert receipt["selection"] == selected
    assert receipt["camera"] == saved["camera"]
    assert receipt["reference_identity"] == selected["materialized_realization_id"]
    assert "display_axes" not in receipt["presentation"]
    if view == "families":
        assert "families.json" in files and "trace.svg" in files
    if view == "similarity":
        trace = ET.fromstring(files["trace.svg"])
        assert float(trace.get("font-size")) * 246 / 1200 >= 7
        overview = ET.fromstring(files["overview.svg"])
        original = ET.fromstring(dict(choices.atlas(saved)._files)["overview.svg"])

        def bases(root):
            return {
                (
                    e.get("data-state-id"),
                    e.get("data-strand-id"),
                    e.get("data-base-index"),
                    e.get("data-base"),
                )
                for e in root.iter()
                if e.get("data-base-index") is not None
            }

        assert bases(overview) == bases(original)
        assert float(overview.get("font-size")) >= 32
    with pytest.raises(ValueError, match="Display axes"):
        choices.figure(view="families", display_axes=axes)
    with pytest.raises(ValueError, match="Display axes"):
        choices.figure(view="similarity", display_axes=axes)


def test_saved_projection_reopens_the_same_browser_trace_and_public_figure(
    captured_choices, tmp_path
):
    choices = captured_choices.freeze(tmp_path / "edition", compact=True, include_landscape=True)
    selection = choices.sample(seed=2)
    axes = ["left_end_word", "left_gap", "right_gap", "right_end_word"]
    before = choices.query()
    saved = choices.view(
        selection,
        presentation={"landscape": "similarity", "display_axes": axes},
        render_policy="current",
    )
    assert saved["schema"] == "hop.atlas-view/v4"
    assert choices.restore_view(saved) == saved
    for invalid in (
        {**saved, "landscape_digest": "sha256:" + "0" * 64},
        {**saved, "landscape_digest": None},
        {**saved, "presentation": {**saved["presentation"], "landscape": "parameters"}},
    ):
        with pytest.raises(ValueError, match=r"coordinate|digest"):
            choices.restore_view(invalid)
    packet = choices.figure(selection=saved)
    assert json.loads(dict(packet._files)["display-projection.json"])["displayed"] == axes
    session = DesignInspectionSession(choices, tmp_path / "browser")
    try:
        opened = session.state()
        state = session.restore({"token": opened["token"], "receipt": saved})
        assert state["selection"] == selection
        assert state["view_receipt"] == saved
        svg = ET.fromstring(
            (session.root / state["plots"]["inspection"].removeprefix("/files/")).read_bytes()
        )
        assert [e.get("data-axis") for e in svg.iter() if e.get("data-axis")] == axes
        assert [v["key"] for v in state["selected_trace"]["values"]] == axes
        hover = session.preview(
            {
                "token": state["token"],
                "materialized_realization_id": selection["materialized_realization_id"],
            }
        )
        assert hover["trace"] == state["selected_trace"]
        assert hover["figure_layout"] == state["figure_layout"]
        assert session.state()["view_receipt"] == saved
        assert choices.query() == before
        # The plot can change while the admitted cohort and exact selection remain.
        changed = session.view(
            {
                "token": state["token"],
                "stage": "all",
                "camera": None,
                "presentation": {
                    **state["presentation"],
                    "display_axes": ["loop_nt", "foldback_arm_bp"],
                },
            }
        )
        assert changed["selection"] == selection
        assert changed["trace_projection"]["projection"] != state["trace_projection"]["projection"]
        assert changed["plots"]["inspection"] != state["plots"]["inspection"]
        assert [v["key"] for v in changed["selected_trace"]["values"]] == [
            "loop_nt",
            "foldback_arm_bp",
        ]
    finally:
        session.close()


@pytest.mark.parametrize(
    "axes", [[], ["left_gap", "left_gap"], ["unknown"], ["loop_side_paired_bp"]]
)
def test_projected_view_rejects_invalid_axis_recipe(captured_choices, axes):
    with pytest.raises(ValueError, match=r"axis|axes|canonical|at least"):
        captured_choices.view(captured_choices.sample(seed=2), presentation={"display_axes": axes})
