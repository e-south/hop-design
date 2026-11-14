"""A saved study map drives browser, view receipts and figure exports together."""

import json

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.design.construction.navigation.inspection_projection import map_index
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.integration.test_atlas_edition import captured_choices  # noqa: F401


@pytest.fixture(scope="module")
def overview_edition(captured_choices, tmp_path_factory):  # noqa: F811
    root = tmp_path_factory.mktemp("recorded-overview") / "collection"
    identity = captured_choices.sample(seed=0)["materialized_realization_id"]
    edition = captured_choices.freeze(root, identities=(identity,), compact=True)
    answer = edition.query()
    path = answer["paths"][0]
    value = path["values"]["left_gap"]
    method = path["values"]["release_method"]
    axis = next(axis for axis in answer["axes"] if axis["key"] == "release_method")
    name = next(node["label"] for node in axis["nodes"] if node["value"] == method)
    overview = {
        "schema": "hop.preparation-overview/v1",
        "snapshot_digest": answer["snapshot_digest"],
        "members": [identity],
        "coordinates": [[1.25, -2.5]],
        "algorithm": "umap",
        "provenance": {},
        "basis": {
            "shape_scales": {"left_gap": 1},
            "sequence_keys": [],
            "interface_keys": [],
            "processing_keys": ["release_method"],
            "weights": [1.0, 1.0, 1.0, 1.0],
        },
        "columns": [
            {
                "key": "shape.left_gap",
                "parameters": ["left_gap"],
                "label": "Left gap",
                "unit": "bp",
                "active": True,
                "dictionary": [value],
                "indices": [0],
            },
            {
                "key": "processing.release_method",
                "parameters": ["release_method"],
                "label": "Release enzyme",
                "unit": "",
                "active": True,
                "dictionary": [method],
                "indices": [0],
                "display_dictionary": [name],
            },
        ],
    }
    content = canonical_json_bytes(overview)
    (root / "overview.json").write_bytes(content)
    manifest = json.loads((root / "edition.json").read_bytes())
    manifest["artifacts"]["overview.json"] = {
        "bytes": len(content),
        "sha256": sha256_digest(content),
    }
    (root / "edition.json").write_bytes(canonical_json_bytes(manifest))
    return construction.load_atlas_edition(root), identity


def test_saved_map_is_shared_by_browser_receipts_and_exports(overview_edition, tmp_path):
    edition, identity = overview_edition
    assert edition.has_landscape
    overview = edition.recorded_overview()
    assert overview["members"] == [identity]
    indexed = map_index(edition, edition.query())
    assert indexed["points"] == [[0, 831.25, 702.5]]
    assert len(indexed["comparison"]["columns"]) == 2
    view = edition.view(
        edition.select(identity), presentation={"landscape": "similarity"}, render_policy="current"
    )
    assert edition.restore_view(view) == view
    packet = edition.figure(selection=view)
    assert json.loads(packet.json_bytes)["overview"]["members"] == [identity]
    assert b"Release enzyme" in dict(packet._files)["comparison-features.svg"]
    receipt = tmp_path / "view.json"
    receipt.write_text(json.dumps(view))
    output = tmp_path / "figure"
    result = CliRunner().invoke(
        app,
        [
            "design",
            "figure",
            str(edition._directory),
            "--selection",
            str(receipt),
            "--out",
            str(output),
        ],
    )
    if result.exception is not None:
        raise result.exception
    assert result.exit_code == 0, result.output
    assert (output / "figure.svg").read_bytes() == dict(packet._files)["figure.svg"]
    exported = edition.retrieve(edition.select(identity), tmp_path / "oligos")
    assert exported.materialized_realization_ids == (identity,)
    assert edition.preview(identity).json_bytes


def test_native_recalculation_cannot_silently_replace_a_recorded_map(overview_edition):
    edition, _ = overview_edition
    with pytest.raises(ValueError, match="recorded preparation overview"):
        edition.landscape()


def test_browser_restores_saved_map_with_its_compact_transport(
    overview_edition, tmp_path, monkeypatch
):
    from hop_design.commands.design.browser import create_design_server
    from hop_design.commands.design.inspection_plots import InspectionPlots

    edition, identity = overview_edition
    view = edition.view(
        edition.select(identity), presentation={"landscape": "similarity"}, render_policy="current"
    )
    receipt = tmp_path / "view.json"
    receipt.write_text(json.dumps(view))
    original = InspectionPlots.get
    calls = []

    def compact_only(self, *args, **kwargs):
        calls.append(kwargs.get("compact"))
        assert kwargs.get("compact") is True, "Browser startup generated redundant full drawings"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(InspectionPlots, "get", compact_only)
    server = create_design_server(edition._directory, tmp_path / "browser", receipt=receipt)
    try:
        state = server.session.response(server.session.state, format="compact-v1")
        assert state["view_receipt"] == view
        assert state["compact"]["members"] == [identity]
        assert calls and all(calls)
    finally:
        server.server_close()
        server.session.close()
