"""Compact editions browse descriptors and render only the selected authority."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.integration.test_atlas_edition import captured_choices as captured_choices


def files(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_descriptor_admission_is_reused_without_reusing_mutable_results(
    captured_choices, tmp_path, monkeypatch
):
    from hop_design.design.construction.editions.descriptors import edition_descriptors
    from hop_design.design.construction.editions.storage import EditionStore
    from hop_design.models.construction.editions.descriptors import CapturedDescriptorIndex

    edition = captured_choices.freeze(tmp_path / "compact", compact=True)
    admitted, checked = [], []
    validate, read = CapturedDescriptorIndex.model_validate_json, EditionStore.read

    def validate_row(raw, **kwargs):
        admitted.append(raw)
        return validate(raw, **kwargs)

    def checked_read(self, name):
        if name == "descriptors.json":
            checked.append(name)
        return read(self, name)

    monkeypatch.setattr(CapturedDescriptorIndex, "model_validate_json", validate_row)
    monkeypatch.setattr(EditionStore, "read", checked_read)
    first = edition_descriptors(edition)
    original = first[0].shape["loop_nt"]
    first[0].shape["loop_nt"] = original + 1
    first[0].sequences.clear()
    first[0].interfaces.clear()
    second = edition_descriptors(edition)
    assert second[0].shape["loop_nt"] == original
    assert second[0].sequences and second[0].interfaces
    assert len(admitted) == 1
    assert checked == ["descriptors.json", "descriptors.json"]
    other = construction.load_atlas_edition(edition._directory)
    assert edition_descriptors(other) == second
    assert len(admitted) == 2


def test_warm_descriptor_admission_rejects_same_length_modified_bytes(captured_choices, tmp_path):
    from hop_design.design.construction.editions.descriptors import edition_descriptors

    edition = captured_choices.freeze(tmp_path / "compact", compact=True)
    edition_descriptors(edition)
    path = edition._directory / "descriptors.json"
    raw = path.read_bytes()
    changed = raw.replace(b'"clone_ready_duplex"', b'"clone_reedy_duplex"', 1)
    assert len(changed) == len(raw) and changed != raw
    path.write_bytes(changed)
    with pytest.raises(ValueError, match="digest"):
        edition_descriptors(edition)


def test_compact_capture_skips_drawings_and_retrieves_exact_materials(
    captured_choices, tmp_path, monkeypatch
):
    choices = captured_choices
    selected = choices.sample(seed=1)
    identity = selected["materialized_realization_id"]
    choices.retrieve(selected, tmp_path / "expected")
    expected_atlas = json.loads(choices.atlas(selected).json_bytes)["atlas"]

    def forbidden(*args, **kwargs):
        pytest.fail("Compact capture must not draw the full cohort")

    with monkeypatch.context() as scoped:
        scoped.setattr(type(choices), "atlas", forbidden)
        edition = choices.freeze(tmp_path / "compact", compact=True)
    assert edition._store.manifest.schema_id == "hop.atlas-edition/v2"
    assert not list(edition._directory.rglob("*.svg"))
    shutil.copytree(edition._directory, tmp_path / "moved")
    monkeypatch.setattr(construction, "load_design_choices", forbidden)
    loaded = construction.load_atlas_edition(tmp_path / "moved")
    selected = loaded.select(identity)
    loaded.retrieve(selected, tmp_path / "actual")
    assert files(tmp_path / "actual") == files(tmp_path / "expected")
    summary = json.loads(loaded.atlas(selected).json_bytes)
    assert summary["atlas"] == expected_atlas
    assert summary["rendering"]["effective"] == "current"
    assert summary["producer"] == edition.producer
    assert identity.encode() in dict(loaded.preview(identity)._files)["overview.svg"]
    receipt = loaded.view(selected)
    assert loaded.restore_view(receipt) == receipt
    figure = loaded.figure(selection=selected)
    assert json.loads(figure.json_bytes)["selection"] == selected


def test_compact_map_does_not_open_authorities_and_selected_corruption_is_rejected(
    captured_choices, tmp_path, monkeypatch
):
    from hop_design.design.construction.editions.storage import EditionStore

    edition = captured_choices.freeze(tmp_path / "compact", compact=True)
    audit = edition.verify_integrity()
    assert audit["authority_archives_verified"] == 1
    assert audit["molecular_replay"] is False
    read = EditionStore.read

    def metadata_only(self, name):
        if name.endswith("evidence.zip"):
            pytest.fail("Map loading must not read complete preparations")
        return read(self, name)

    with monkeypatch.context() as scoped:
        scoped.setattr(EditionStore, "read", metadata_only)
        loaded = construction.load_atlas_edition(edition._directory)
        assert len(loaded.landscape().preparations) == 1
    archive = next(edition._directory.rglob("evidence.zip"))
    content = bytearray(archive.read_bytes())
    content[len(content) // 2] ^= 1
    archive.write_bytes(content)
    with pytest.raises(ValueError, match="digest"):
        loaded.verify_integrity()
    with pytest.raises(ValueError, match="digest"):
        loaded.retrieve(loaded.sample(seed=1), tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_compact_freeze_uses_existing_cli(captured_choices, tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "design",
            "freeze",
            str(captured_choices._directory),
            "--compact",
            "--out",
            str(tmp_path / "compact"),
        ],
    )
    assert result.exit_code == 0, result.output
    loaded = construction.load_atlas_edition(tmp_path / "compact")
    assert loaded._store.manifest.schema_id == "hop.atlas-edition/v2"


def test_state_validation_uses_verified_route_without_projecting_teaching(
    captured_choices, tmp_path, monkeypatch
):
    edition = captured_choices.freeze(tmp_path / "compact", compact=True)
    selected = edition.sample(seed=1)
    atlas = json.loads(edition.atlas(selected).json_bytes)["atlas"]
    expected = tuple(s["state"]["state_id"] for s in atlas["states"])

    def forbidden(*args, **kwargs):
        pytest.fail("State validation must not project the teaching molecule")

    monkeypatch.setattr(
        "hop_design.design.construction.editions.compact_projection.project_molecular_atlas",
        forbidden,
    )
    assert edition._view_state_ids(selected) == expected
    descriptor = edition._directory / "descriptors.json"
    raw = descriptor.read_bytes()
    descriptor.write_bytes(raw.replace(b'"clone_ready_duplex"', b'"clone_reedy_duplex"', 1))
    with pytest.raises(ValueError, match="digest"):
        edition._view_state_ids(selected)


def test_receipt_checks_fresh_landscape_bytes_without_requerying_cohort(
    captured_choices, tmp_path, monkeypatch
):
    edition = captured_choices.freeze(tmp_path / "compact", compact=True, include_landscape=True)
    selected = edition.sample(seed=1)
    expected_digest = edition.landscape().digest
    original, calls = edition._store.read, []
    query, queries = edition.query, []

    def counted(name):
        if name == "landscape.json":
            calls.append(name)
        return original(name)

    def counted_query(*args, **kwargs):
        queries.append(1)
        return query(*args, **kwargs)

    monkeypatch.setattr(edition._store, "read", counted)
    monkeypatch.setattr(edition, "query", counted_query)
    receipt = edition.view(selected, presentation={"landscape": "similarity"})
    assert receipt["landscape_digest"] == expected_digest
    assert len(calls) == 1
    assert not queries, "Saving a view needs membership, not whole-cohort facet statistics"
    assert edition.restore_view(receipt) == receipt
    assert len(calls) == 2
    assert not queries
    path = edition._directory / "landscape.json"
    raw = path.read_bytes()
    path.write_bytes(raw.replace(b'"clone_ready_duplex"', b'"clone_reedy_duplex"', 1))
    with pytest.raises(ValueError, match="digest"):
        edition.view(selected, presentation={"landscape": "similarity"})


@pytest.mark.parametrize("stage", ["endpoint", "hairpin"])
def test_compact_inspection_reuses_admitted_cohort_for_distributions(
    captured_choices, tmp_path, monkeypatch, stage
):
    from hop_design.commands.design.inspection_plots import InspectionPlots
    from hop_design.commands.design.inspection_view import initial_state

    edition = captured_choices.freeze(tmp_path / "compact", compact=True, include_landscape=True)
    state = initial_state(edition)
    state["family_stage"] = stage
    expected = edition.plot_svg_bytes(view="distributions", stage=stage)
    families = edition.families(stage=stage)

    def forbidden(*args, **kwargs):
        pytest.fail("Compact inspection must project its already-admitted cohort")

    monkeypatch.setattr(edition, "families", forbidden)
    monkeypatch.setattr(edition, "plot_svg_bytes", forbidden)
    plots = InspectionPlots(tmp_path)
    try:
        result = plots.get(edition, state, compact=True)
        path = tmp_path / result["plots"]["distributions"].removeprefix("/files/")
        assert path.read_bytes() == expected
        assert result["cohort_summary"] == {
            "product": families["product"],
            "products": len(families["products"]),
            "eligible_products": sum(
                bool(p["eligible_preparations"]) for p in families["products"]
            ),
        }
    finally:
        plots.close()


@pytest.mark.parametrize("compact_transport", [False, True])
def test_inspection_transports_share_current_labels_without_rewriting_admitted_answers(
    captured_choices, tmp_path, monkeypatch, compact_transport
):
    from hop_design.commands.design.inspection import DesignInspectionSession

    edition = captured_choices.freeze(tmp_path / "edition", compact=True, include_landscape=True)
    query = edition.query

    def historical_query(*args, **kwargs):
        answer = query(*args, **kwargs)
        for axis in answer["axes"]:
            if axis["key"] == "left_gap":
                axis["label"] = "Left end-to-stem gap"
        return answer

    monkeypatch.setattr(edition, "query", historical_query)
    session = DesignInspectionSession(edition, tmp_path / "inspection")
    try:
        response = session.response(
            session.state, format="compact-v1" if compact_transport else None
        )
        shown = response["compact"]["choices"] if compact_transport else response["choices"]
        assert next(a for a in shown["axes"] if a["key"] == "left_gap")["label"] == "Left gap"
        assert (
            next(a for a in session._state["choices"]["axes"] if a["key"] == "left_gap")["label"]
            == "Left end-to-stem gap"
        )
        assert shown["parameter_label_projection"]["renamed"] == [
            {"key": "left_gap", "captured_label": "Left end-to-stem gap", "label": "Left gap"}
        ]
        again = session.response(
            session.state,
            cohort=response["cohort"],
            format="compact-v1" if compact_transport else None,
        )
        assert again["cohort_unchanged"] and "choices" not in again and "compact" not in again
        assert again["plots"] == response["plots"]
    finally:
        session.close()
