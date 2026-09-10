"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_basal_source_view.py

Tests source-duplex drawing facts from public basal-discovery receipts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import hop_design.views as views
from hop_design.construction import discover_local_neighborhood, load_verified_local_neighborhood

EXAMPLE = Path(__file__).resolve().parents[2] / "examples/basal-junction/request.yaml"


@pytest.fixture
def basal_request() -> dict:
    request = yaml.safe_load(EXAMPLE.read_text())
    request["geometry_domain"]["nick_offsets_nt"] = [0]
    request["geometry_domain"]["future_release"]["cohesive_end_sequence"] = "CTCA"
    return request


def _discover(request: dict, tmp_path: Path):
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    return discover_local_neighborhood(path)


def _first_id(receipt) -> str:
    return json.loads(receipt.json_bytes)["realizations"][0]["local_realization"][
        "local_realization_id"
    ]


def test_basal_source_panel_shows_two_sites_and_only_the_present_nick(
    basal_request: dict, tmp_path: Path
) -> None:
    receipt = _discover(basal_request, tmp_path)
    before = receipt.json_bytes
    panel = views.build_basal_source_panel(receipt, realization_id=_first_id(receipt))

    assert isinstance(panel, views.ViewPanel)
    assert panel.panel_id == "basal_source"
    assert panel.tracks[0].sequence == "GAAGACGTCTCAATAACTTCGTATAGCATACATTATACGAAGTTAT"
    features = {feature.feature_id: feature for feature in panel.features}
    assert set(features) == {"payload", "nickase_site_0", "basal_nick", "future_release_site"}
    for name, start, end in (
        ("payload", 12, 46),
        ("nickase_site_0", 6, 11),
        ("basal_nick", 12, 12),
        ("future_release_site", 0, 6),
    ):
        feature = features[name]
        assert feature.track_id == "source_top"
        assert (feature.span.start.offset, feature.span.end.offset) == (start, end)
    assert features["nickase_site_0"].label == "Nt.BsmAI"
    assert features["future_release_site"].label == "BbsI (later processing)"
    assert len(panel.pairings) == 46
    assert all(pair.kind == "watson_crick" for pair in panel.pairings)
    assert receipt.json_bytes == before
    output = receipt.write(tmp_path / "result")
    loaded = load_verified_local_neighborhood(output / "result.json")
    assert views.build_basal_source_panel(loaded, realization_id=_first_id(loaded)) == panel
    assert views.ViewPanel.model_validate_json(panel.model_dump_json()) == panel


def test_bottom_nick_uses_intrinsic_coordinates_on_an_antiparallel_track(
    basal_request: dict, tmp_path: Path
) -> None:
    basal_request["endpoint"] = "hairpin_pcr_duplex"
    geometry = basal_request["geometry_domain"]
    del geometry["future_release"]
    geometry["nick_strand"] = "bottom"
    geometry["nick_offsets_nt"] = [6]
    basal_request["search"]["max_retained_overhead_nt"] = 10
    receipt = _discover(basal_request, tmp_path)

    panel = views.build_basal_source_panel(receipt, realization_id=_first_id(receipt))

    top, bottom = panel.tracks
    assert top.sequence == "AAAAAGAGACATAACTTCGTATAGCATACATTATACGAAGTTAT"
    assert bottom.sequence == "ATAACTTCGTATAATGTATGCTATACGAAGTTATGTCTCTTTTT"
    assert top.direction == "5to3"
    assert bottom.direction == "3to5"
    nick = next(feature for feature in panel.features if feature.feature_id == "basal_nick")
    assert nick.track_id == "source_bottom"
    assert (nick.span.start.offset, nick.span.end.offset) == (40, 40)
    assert [(pair.left_index, pair.right_index) for pair in panel.pairings] == [
        (i, 43 - i) for i in range(44)
    ]
    assert "future_release_site" not in {feature.feature_id for feature in panel.features}


def test_endpoint_supplied_site_is_not_drawn_as_source_encoded(
    basal_request: dict, tmp_path: Path
) -> None:
    basal_request["geometry_domain"]["future_release"]["recognition_material"] = "endpoint_material"
    receipt = _discover(basal_request, tmp_path)

    panel = views.build_basal_source_panel(receipt, realization_id=_first_id(receipt))

    assert "future_release_site" not in {feature.feature_id for feature in panel.features}
    assert not any("BbsI" in feature.label for feature in panel.features)


def test_source_panel_rejects_an_unknown_selection(basal_request: dict, tmp_path: Path) -> None:
    receipt = _discover(basal_request, tmp_path)
    with pytest.raises(ValueError, match="Unknown basal local realization"):
        views.build_basal_source_panel(receipt, realization_id="missing")


def test_source_panel_rejects_a_corrupt_receipt(basal_request: dict, tmp_path: Path) -> None:
    receipt = _discover(basal_request, tmp_path)
    realization_id = _first_id(receipt)
    object.__setattr__(receipt, "_json_bytes", b"{}\n")
    with pytest.raises(ValueError, match="content disagrees"):
        views.build_basal_source_panel(receipt, realization_id=realization_id)


def test_source_panel_rejects_a_foldback_receipt(basal_request: dict, tmp_path: Path) -> None:
    basal_request["family"] = "foldback"
    basal_request["endpoint"] = "ssdna_hairpin"
    basal_request["geometry_domain"] = {
        "family": "foldback",
        "nick_strand": "top",
        "junction_offsets_nt": [0],
        "loop_lengths_nt": [3],
        "annealing_arm_lengths_bp": [3],
    }
    receipt = _discover(basal_request, tmp_path)
    with pytest.raises(ValueError, match="requires a basal-neighborhood receipt"):
        views.build_basal_source_panel(receipt, realization_id="missing")
