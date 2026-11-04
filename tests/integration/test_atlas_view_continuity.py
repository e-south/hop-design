"""Saved inspections resume the same experiment-facing navigation in a fresh session."""

import json
import shutil
from contextlib import closing
from xml.etree import ElementTree as ET

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.commands.design.inspection import DesignInspectionSession
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.integration.test_atlas_edition import captured_choices, captured_edition  # noqa: F401


def test_saved_color_reopens_same_preparation_and_colors_api_cli_exports(
    captured_choices,  # noqa: F811
    tmp_path,
    monkeypatch,
):
    choices = captured_choices.freeze(
        tmp_path / "color-edition", compact=True, include_landscape=True
    )
    selected = choices.sample(seed=1)
    answer = choices.query()
    word = answer["paths"][0]["values"]["left_end_word"]
    lens = {"key": "left_end_word", "word": word}
    saved = choices.view(selected, presentation={"landscape": "similarity", "color": lens})
    assert saved["schema"] == "hop.atlas-view/v5"
    assert choices.restore_view(saved) == saved
    assert saved["selection"] == selected
    packet = choices.figure(selection=saved)
    files = dict(packet._files)
    plot = ET.fromstring(files["plot.svg"])
    assert plot.get("data-color-key") == "left_end_word"
    assert plot.get("data-color-word") == word
    assert json.loads(files["view.json"]) == saved
    source = tmp_path / "color-view.json"
    source.write_text(json.dumps(saved))
    result = CliRunner().invoke(
        app,
        [
            "design",
            "figure",
            str(choices._directory),
            "--selection",
            str(source),
            "--out",
            str(tmp_path / "colored"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "colored" / "plot.svg").read_bytes() == files["plot.svg"]
    assert json.loads((tmp_path / "colored" / "view.json").read_bytes()) == saved
    with closing(DesignInspectionSession(choices, tmp_path / "color-browser")) as session:
        initial = session.state()
        with pytest.raises(ValueError, match="recorded pool"):
            session.view(
                {
                    "token": initial["token"],
                    "stage": "all",
                    "camera": None,
                    "presentation": {
                        **initial["presentation"],
                        "color": {"key": "loop_word", "word": "A" * 100},
                    },
                }
            )
        assert session.state()["token"] == initial["token"]
        restored = session.restore({"token": session.state()["token"], "receipt": saved})
        assert restored["presentation"]["color"] == lens
        assert restored["selection"] == selected
        original_plots = restored["plots"]

        def forbidden(*args, **kwargs):
            pytest.fail("A color-only saved view must not rebuild molecular drawings")

        monkeypatch.setattr(choices, "atlas", forbidden)
        changed = session.view(
            {
                "token": restored["token"],
                "stage": "all",
                "camera": None,
                "presentation": {**restored["presentation"], "color": {"key": "none"}},
            }
        )
        assert changed["plots"] == original_plots
        assert changed["selection"] == selected
    absent = {
        **saved,
        "presentation": {**saved["presentation"], "color": {"key": "loop_word", "word": "A" * 100}},
    }
    with pytest.raises(ValueError, match="recorded pool"):
        choices.restore_view(absent)
    assert choices.query() == answer


def test_complete_view_restores_and_resumes_through_api_cli_and_session(
    captured_edition,  # noqa: F811
    tmp_path,
):
    choices = captured_edition
    selected = choices.sample(seed=7)
    identity = selected["materialized_realization_id"]
    presentation = {
        "landscape": "families",
        "molecule": "route",
        "family_stage": "hairpin",
        "layout": "mosaic",
        "route": "complete",
    }
    exploration = {"seed": 8, "strategy": "families", "history": [identity]}
    receipt = choices.view(
        selected, camera=(1, 2, 100, 80), presentation=presentation, exploration=exploration
    )
    assert receipt["schema"] == "hop.atlas-view/v2"
    assert receipt["presentation"] == presentation
    assert receipt["exploration"] == exploration
    expected = choices.sample(seed=8, strategy="families", stage="hairpin", history=(identity,))
    assert choices.sample(after=receipt) == expected
    assert choices.atlas(receipt).svg_bytes == choices.atlas(selected).svg_bytes
    source = tmp_path / "view.json"
    source.write_text(json.dumps(receipt))
    result = CliRunner().invoke(
        app, ["design", "sample", str(choices._directory), "--after", str(source)]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == expected
    session = DesignInspectionSession(choices, tmp_path / "reopened")
    try:
        state = session.restore({"token": session.state()["token"], "receipt": receipt})
        assert state["view_receipt"] == receipt
        assert state["family_stage"] == "hairpin"
        sampled = session.sample({"token": state["token"]})
        assert sampled["sample_receipt"] == expected
        assert sampled["view_receipt"]["presentation"] == presentation
        assert sampled["view_receipt"]["camera"] == [1.0, 2.0, 100.0, 80.0]
    finally:
        session.close()


def test_legacy_view_has_explicit_defaults_and_invalid_context_fails_closed(
    captured_edition,  # noqa: F811
):
    choices = captured_edition
    selected = choices.sample(seed=0)
    old = {
        "schema": "hop.atlas-view/v1",
        "pool_digest": choices.digest,
        "selection": selected,
        "stage": "all",
        "reference_identity": None,
        "camera": None,
    }
    restored = choices.restore_view(old)
    assert restored["schema"] == "hop.atlas-view/v2"
    assert restored["presentation"] == {
        "landscape": "parameters",
        "molecule": "molecule",
        "family_stage": "endpoint",
        "layout": "auto",
        "route": "complete",
    }
    assert restored["exploration"] == {"seed": 0, "strategy": "families", "history": []}
    for invalid in (
        {**old, "schema": "hop.atlas-view/v100"},
        {**old, "invented": True},
        {**restored, "exploration": {"seed": 0, "history": ["missing-preparation"]}},
        {**restored, "presentation": {"family_stage": "invented-stage"}},
    ):
        with pytest.raises(ValueError):
            choices.restore_view(invalid)


def test_inspection_is_compact_and_camera_does_not_regenerate_figures(
    captured_edition,  # noqa: F811
    tmp_path,
    monkeypatch,
):
    session = DesignInspectionSession(captured_edition, tmp_path / "compact")
    try:
        state = session.sample({"token": session.state()["token"], "seed": 0})
        assert len(json.dumps(state).encode()) < 1_020_239
        preview = state["preview"]
        assert "molecules" not in preview["summary"]["atlas"]["states"][0]["state"]
        raw = json.loads((session.root / preview["record"].removeprefix("/files/")).read_bytes())
        assert raw["atlas"]["states"][0]["state"]["molecules"]
        assert (
            raw["atlas"]["materialized_realization_id"]
            == state["selection"]["materialized_realization_id"]
        )
        artifacts = state["plots"]
        for url in artifacts.values():
            assert (session.root / url.removeprefix("/files/")).is_file()

        def forbidden(*args, **kwargs):
            pytest.fail("A camera-only action must reuse the recorded drawings")

        monkeypatch.setattr(captured_edition, "plot_svg_bytes", forbidden)
        monkeypatch.setattr(captured_edition, "atlas", forbidden)
        after = session.view({"token": state["token"], "stage": "all", "camera": [2, 3, 90, 70]})
        assert after["plots"] == artifacts
        cache = session.cache_root
    finally:
        session.close()
    assert not cache.exists()


@pytest.mark.parametrize("artifact", ["summary.json", "projection.svg", "teaching.svg"])
def test_lightweight_view_restore_still_rejects_changed_captured_artifacts(
    captured_edition,  # noqa: F811
    tmp_path,
    artifact,
):
    root = tmp_path / "changed-edition"
    shutil.copytree(captured_edition._directory, root)
    choices = construction.load_atlas_edition(root)
    selected = choices.sample(seed=0)
    receipt = choices.view(selected)
    manifest = json.loads((root / "edition.json").read_bytes())
    member = next(
        m
        for m in manifest["members"]
        if m["materialized_realization_id"] == selected["materialized_realization_id"]
    )
    target = root / member["directory"] / "atlas" / artifact
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="digest disagrees"):
        choices.restore_view(receipt)


def test_comparison_keeps_captured_artwork_unless_redraw_is_explicit(
    captured_edition,  # noqa: F811
    monkeypatch,
):
    selected = captured_edition.sample(seed=0)
    original = captured_edition.atlas(selected)

    def forbidden(*args, **kwargs):
        pytest.fail("Adding a comparison must not implicitly redraw captured molecular artwork")

    monkeypatch.setattr(
        "hop_design.design.construction.navigation.route_comparison.render_molecular_atlas",
        forbidden,
    )
    compared = captured_edition.atlas(selected, reference_selection=selected)
    assert compared.svg_bytes == original.svg_bytes
    assert dict(compared._files)["overview.svg"] == dict(original._files)["overview.svg"]
    summary = json.loads(compared.json_bytes)
    assert summary["comparison"]
    assert summary["rendering"]["effective"] == "captured"
    with pytest.raises(ValueError, match="render"):
        captured_edition.atlas(selected, render_policy="invented")


@pytest.mark.parametrize("landscape", ["families", "parameters"])
def test_saved_view_drives_api_and_cli_figure_exports(
    captured_choices,  # noqa: F811
    captured_edition,  # noqa: F811
    tmp_path,
    landscape,
):
    for name, choices in (("live", captured_choices), ("edition", captured_edition)):
        selected = choices.sample(seed=0)
        receipt = choices.view(
            selected,
            reference_identity=selected["materialized_realization_id"],
            camera=(2, 3, 400, 200),
            presentation={
                "landscape": landscape,
                "molecule": "route",
                "family_stage": "hairpin",
                "layout": "mosaic" if landscape == "families" else "auto",
            },
            exploration={
                "seed": 19,
                "strategy": "families",
                "history": [selected["materialized_realization_id"]],
            },
            render_policy="current",
        )
        expected = choices.atlas(receipt)
        figure = choices.figure(selection=receipt)
        facts = json.loads(figure.json_bytes)
        assert facts["view_receipt"] == receipt
        assert facts["rendering"] == json.loads(expected.json_bytes)["rendering"]
        assert dict(figure._files)["teaching.svg"] == dict(expected._files)["teaching.svg"]
        assert ("families.json" in dict(figure._files)) == (landscape == "families")
        assert json.loads(dict(figure._files)["view.json"]) == receipt
        source = tmp_path / f"{name}-view.json"
        source.write_text(json.dumps(receipt))
        output = tmp_path / name
        result = CliRunner().invoke(
            app,
            [
                "design",
                "figure",
                str(choices._directory),
                "--selection",
                str(source),
                "--out",
                str(output),
            ],
        )
        assert result.exit_code == 0, result.output
        assert json.loads((output / "view.json").read_text()) == receipt
        assert (output / "figure.svg").read_bytes() == dict(figure._files)["figure.svg"]


def test_unsupported_current_drawing_keeps_captured_artwork_with_comparison(
    captured_edition,  # noqa: F811
    tmp_path,
):
    root = tmp_path / "future-edition"
    shutil.copytree(captured_edition._directory, root)
    manifest = json.loads((root / "edition.json").read_bytes())
    member = manifest["members"][0]
    path = member["directory"] + "/atlas/summary.json"
    summary = json.loads((root / path).read_bytes())
    summary["atlas"]["future_presentation_feature"] = True
    content = canonical_json_bytes(summary)
    (root / path).write_bytes(content)
    manifest["artifacts"][path] = {"sha256": sha256_digest(content), "bytes": len(content)}
    (root / "edition.json").write_bytes(canonical_json_bytes(manifest))
    edition = construction.load_atlas_edition(root)
    selected = edition.select(member["materialized_realization_id"])
    expected = edition.atlas(selected)
    for reference in (None, selected):
        packet = edition.atlas(selected, reference_selection=reference, render_policy="current")
        rendering = json.loads(packet.json_bytes)["rendering"]
        assert rendering["requested"] == "current"
        assert rendering["effective"] == "captured"
        assert "not supported" in rendering["notice"]
        assert packet.svg_bytes == expected.svg_bytes
        assert dict(packet._files)["teaching.svg"] == dict(expected._files)["teaching.svg"]
