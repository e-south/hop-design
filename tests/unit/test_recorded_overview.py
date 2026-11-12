"""Recorded coordinates keep preparation membership and the declared comparison."""

import copy
from xml.etree import ElementTree as ET

import pytest

from hop_design.models.construction.variants.overview import PreparationOverview


def document():
    return {
        "schema": "hop.preparation-overview/v1",
        "snapshot_digest": "sha256:" + "a" * 64,
        "members": ["A", "B"],
        "coordinates": [[0.0, 0.0], [1.0, 2.0]],
        "basis": {
            "shape_scales": {"left_gap": 4},
            "sequence_keys": [],
            "interface_keys": [],
            "processing_keys": ["release_method"],
            "weights": [1.0, 1.0, 1.0, 1.0],
        },
        "columns": [
            {
                "key": "shape.left_gap",
                "label": "Left gap",
                "unit": "bp",
                "parameters": ["left_gap"],
                "active": True,
                "dictionary": [0],
                "indices": [0, 0],
            },
            {
                "key": "processing.release_method",
                "label": "Release enzyme",
                "unit": "",
                "parameters": ["release_method"],
                "active": True,
                "dictionary": ["enzyme-a"],
                "indices": [0, 0],
                "display_dictionary": ["Enzyme A"],
            },
        ],
        "algorithm": "umap",
        "provenance": {"source": "sha256:" + "b" * 64},
    }


def test_equal_comparison_values_retain_every_preparation_and_its_saved_coordinate():
    overview = PreparationOverview.model_validate_json(__import__("json").dumps(document()))
    assert overview.members == ("A", "B")
    assert overview.coordinates == ((0.0, 0.0), (1.0, 2.0))
    from hop_design.export.construction.survey.recorded_overview import (
        comparison_packet,
        overview_map_index,
    )

    assert comparison_packet(overview, ("B", "A"))["columns"][0]["indices"] == [0, 0]
    assert len(overview_map_index(overview, ("B", "A"))["points"]) == 2
    assert overview_map_index(overview, ("B", "A"))["points"][0][0] == 1


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["members"].append("C"),
        lambda d: d["members"].__setitem__(1, "A"),
        lambda d: d["coordinates"].__setitem__(1, [float("nan"), 0]),
        lambda d: d["columns"][0]["indices"].__setitem__(1, 9),
        lambda d: d["columns"][0].__setitem__("key", "shape.imaginary"),
        lambda d: d["basis"]["shape_scales"].__setitem__("left_gap", 0),
    ],
)
def test_invalid_recorded_maps_fail_before_display(change):
    raw = document()
    change(raw)
    with pytest.raises(ValueError):
        PreparationOverview.model_validate_json(__import__("json").dumps(raw))


def test_binding_rejects_a_valid_but_wrong_comparison_value():
    from hop_design.design.construction.editions.overview import validate_overview

    overview = PreparationOverview.model_validate_json(__import__("json").dumps(document()))
    answer = {
        "snapshot_digest": document()["snapshot_digest"],
        "paths": [
            {
                "materialized_realization_id": k,
                "values": {"left_gap": 0, "release_method": "enzyme-a"},
            }
            for k in ("A", "B")
        ],
        "axes": [{"key": "release_method", "nodes": [{"value": "enzyme-a", "label": "Enzyme A"}]}],
    }
    validate_overview(overview, answer, {})
    changed = copy.deepcopy(answer)
    changed["paths"][1]["values"]["left_gap"] = 1
    with pytest.raises(ValueError, match="value"):
        validate_overview(overview, changed, {})


def test_processing_changes_contribute_by_identity_in_the_declared_group():
    from hop_design.design.construction.navigation.numerical.overview import overview_difference

    raw = document()
    raw["columns"][1].update(
        dictionary=["enzyme-a", "enzyme-b"],
        indices=[0, 1],
        display_dictionary=["Enzyme A", "Enzyme B"],
    )
    overview = PreparationOverview.model_validate_json(__import__("json").dumps(raw))
    difference = overview_difference(overview, 0, 1)
    assert difference.shape == 0 and difference.processing == 1
    assert difference.total == 0.5  # Two nonempty groups, each with unit weight.


def test_standalone_export_fits_the_saved_coordinate_extent():
    from hop_design.export.construction.survey.recorded_overview import render_recorded_overview

    raw = document()
    raw["coordinates"] = [[-15.0, -10.0], [22.0, 27.0]]
    overview = PreparationOverview.model_validate_json(__import__("json").dumps(raw))
    svg = ET.fromstring(render_recorded_overview(overview, eligible={"A", "B"}))
    x, y, width, height = map(float, svg.get("viewBox").split())
    points = [node for node in svg.iter() if node.tag.endswith("circle")]
    assert len(points) == 2
    assert all(x <= float(p.get("cx")) <= x + width for p in points)
    assert all(y <= float(p.get("cy")) <= y + height for p in points)
    units_per_pixel = max(width / 1200, height / 480)
    assert all(float(p.get("r")) / units_per_pixel == pytest.approx(1.35) for p in points)
    assert not any(node.get("data-map-context") for node in svg.iter())
