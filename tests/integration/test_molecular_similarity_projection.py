"""Comparison features come from complete molecular records and actual cuts."""

from hop_design.design.construction.editions.comparison import captured_route
from hop_design.design.construction.navigation.molecular_descriptor import molecular_descriptor
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from tests.integration.test_atlas_edition import captured_choices, captured_edition  # noqa: F401


def test_comparison_tracks_retained_anatomy_and_recorded_receiving_ends(captured_edition):  # noqa: F811
    choice = captured_edition.sample(seed=0)
    route = captured_route(captured_edition, choice["materialized_realization_id"])
    anatomy = describe_hairpin(route)
    descriptor = molecular_descriptor(route)
    assert descriptor.identity == choice["materialized_realization_id"]
    assert descriptor.stem == route.design.payload_sequence
    assert descriptor.shape["loop_nt"] == anatomy.loop_nt
    assert descriptor.shape["loop_side_paired_bp"] == anatomy.loop_side_paired_bp
    assert len(descriptor.sequences["basal_pairs"]) == anatomy.open_side_paired_positions
    assert descriptor.interfaces is not None
    assert descriptor.interfaces["left_word"] == route.final_product.cohesive_ends[0].sequence
    assert descriptor.interfaces["right_word"] == route.final_product.cohesive_ends[1].sequence
    path = next(
        p
        for p in captured_edition.query()["paths"]
        if p["materialized_realization_id"] == descriptor.identity
    )
    assert descriptor.shape["left_gap"] == path["values"]["left_gap"]
    assert descriptor.shape["right_gap"] == path["values"]["right_gap"]
    assert set(descriptor.sequences) == {"loop", "basal_pairs", "foldback_pairs"}


def test_shared_landscape_uses_full_pool_and_freezes_without_refitting(
    captured_choices,  # noqa: F811
    captured_edition,  # noqa: F811
    tmp_path,
    monkeypatch,
):
    for choices in (captured_choices, captured_edition):
        before = choices.query()
        landscape = choices.landscape()
        assert {p.identity for p in landscape.preparations} == {
            p["materialized_realization_id"] for p in before["paths"]
        }
        assert choices.query() == before
        assert choices.landscape() == landscape
    edition = captured_edition.freeze(tmp_path / "with-landscape", include_landscape=True)
    assert edition.producer == captured_edition.producer
    expected = edition.landscape()

    def forbidden(*args, **kwargs):
        raise AssertionError("Viewing saved coordinates must never refit them")

    monkeypatch.setattr(
        "hop_design.design.construction.navigation.similarity_layout.build_molecular_landscape",
        forbidden,
    )
    assert edition.landscape() == expected
    query = {"parameters": [{"key": "loop_nt", "values": [100]}]}
    assert edition.query(query)["matching_preparations"] == 0
    assert edition.landscape() == expected
    selected = edition.sample(seed=0)
    assert selected["materialized_realization_id"] in {p.identity for p in expected.preparations}


def test_cli_can_capture_existing_edition_with_molecular_coordinates(captured_edition, tmp_path):  # noqa: F811
    from typer.testing import CliRunner

    from hop_design import construction
    from hop_design.cli import app

    result = CliRunner().invoke(
        app,
        [
            "design",
            "freeze",
            str(captured_edition._directory),
            "--out",
            str(tmp_path / "frozen"),
            "--include-landscape",
        ],
    )
    assert result.exit_code == 0, result.output
    edition = construction.load_atlas_edition(tmp_path / "frozen")
    assert edition.landscape().snapshot_digest == captured_edition.query()["snapshot_digest"]
    assert edition.producer == captured_edition.producer


def test_undirected_contacts_keep_the_same_molecular_comparison(
    captured_edition,  # noqa: F811
    monkeypatch,
):
    choice = captured_edition.sample(seed=0)
    route = captured_route(captured_edition, choice["materialized_realization_id"])
    anatomy = describe_hairpin(route)
    reversed_contacts = tuple(
        p.model_copy(
            update={
                "left_strand_id": p.right_strand_id,
                "right_strand_id": p.left_strand_id,
                "left_index": p.right_index,
                "right_index": p.left_index,
                "left_base": p.right_base,
                "right_base": p.left_base,
            }
        )
        for p in reversed(anatomy.state.pairings)
    )
    expected = molecular_descriptor(route)
    original = route.model_dump_json()
    # Exercise the read-only anatomy seam; do not forge a new sealed route identity.
    alternate = anatomy.model_copy(
        update={"state": anatomy.state.model_copy(update={"pairings": reversed_contacts})}
    )
    monkeypatch.setattr(
        "hop_design.design.construction.navigation.molecular_descriptor.describe_hairpin",
        lambda _: alternate,
    )
    assert molecular_descriptor(route) == expected
    assert route.model_dump_json() == original


def test_similarity_figure_and_cli_use_the_same_selection_and_coordinates(
    captured_edition,  # noqa: F811
    tmp_path,
):
    import json

    from typer.testing import CliRunner

    from hop_design.cli import app

    selection = captured_edition.sample(seed=0)
    identity = selection["materialized_realization_id"]
    expected = captured_edition.figure(view="similarity", selection=selection)
    facts = json.loads(expected.json_bytes)
    assert facts["selection"] == selection
    assert facts["landscape"]["snapshot_digest"] == captured_edition.query()["snapshot_digest"]
    assert identity.encode() in dict(expected._files)["plot.svg"]
    files = dict(expected._files)
    assert identity.encode() in files["overview.svg"]
    assert b'data-selected="true"' in files["trace.svg"]
    comparison = json.loads(files["comparison-features.json"])
    assert comparison["identity"] == identity
    assert identity.encode() in files["comparison-features.svg"]
    from hop_design.models.construction.variants.similarity import MolecularComparisonBasis

    assert comparison["basis"] == MolecularComparisonBasis.model_validate_json(
        json.dumps(facts["landscape"]["basis"])
    ).model_dump(mode="json", exclude={"comparison_keys"})
    from xml.etree import ElementTree as ET

    panels = ET.fromstring(files["figure.svg"]).findall("*[@data-figure-panel]")
    assert [p.get("data-figure-panel") for p in panels] == ["hairpin", "trace"]
    assert ET.fromstring(files["figure.svg"]).get("data-figure-layout")
    assert ET.fromstring(files["plot.svg"]).get("data-landscape-digest")
    selected_file = tmp_path / "selected.json"
    selected_file.write_text(json.dumps(selection))
    result = CliRunner().invoke(
        app,
        [
            "design",
            "figure",
            str(captured_edition._directory),
            "--selection",
            str(selected_file),
            "--view",
            "similarity",
            "--out",
            str(tmp_path / "figure"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "figure/figure.svg").read_bytes() == dict(expected._files)["figure.svg"]
    assert json.loads((tmp_path / "figure/landscape.json").read_bytes()) == facts["landscape"]


def test_saved_similarity_view_binds_coordinates_and_rejects_a_changed_map(
    captured_edition,  # noqa: F811
    tmp_path,
):
    import json

    import pytest

    edition = captured_edition.freeze(tmp_path / "mapped", include_landscape=True)
    selection = edition.sample(seed=0)
    receipt = edition.view(selection, presentation={"landscape": "similarity"})
    assert receipt["schema"] == "hop.atlas-view/v3"
    assert receipt["landscape_digest"] == edition.landscape().digest
    assert edition.restore_view(receipt) == receipt
    packet = edition.figure(selection=receipt)
    assert json.loads(packet.json_bytes)["view_receipt"] == receipt
    with pytest.raises(ValueError, match="coordinates"):
        edition.restore_view({**receipt, "landscape_digest": "sha256:" + "0" * 64})
    # Old views retain their explicit landscape and do not acquire a map silently.
    legacy = edition.view(selection)
    assert legacy["schema"] == "hop.atlas-view/v2"
    assert "landscape_digest" not in legacy
    assert edition.restore_view(legacy) == legacy
