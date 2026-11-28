"""
--------------------------------------------------------------------------------
HOP Design
hop-design/tests/unit/test_recorded_overview.py

Check saved coordinates, preparation membership and comparison features.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import copy
import json
from xml.etree import ElementTree as ET

import pytest

from hop_design.models.construction.variants.overview import PreparationOverview
from tests.unit.test_molecular_similarity import molecule


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


@pytest.fixture
def complete_binding():
    descriptors = {
        identity: molecule(identity=identity, loop="AC", gap=gap)
        for identity, gap in (("A", 0), ("B", 4))
    }
    raw = document()
    raw["columns"][0].update(dictionary=[0, 4], indices=[0, 1])
    sequences = {
        "loop": ["A", "C"],
        "basal_pairs": [["A", "T", "watson_crick"]],
        "foldback_pairs": [["A", "T", "watson_crick"], ["G", "C", "watson_crick"]],
    }
    interfaces = {
        "left_word": "AGTC",
        "right_word": "AACC",
        "left_polarity": "five_prime",
        "right_polarity": "five_prime",
    }
    raw["basis"].update(sequence_keys=list(sequences), interface_keys=list(interfaces))
    columns = [
        {
            "key": f"{block}.{key}",
            "label": key,
            "unit": "",
            "parameters": [key],
            "active": True,
            "dictionary": [value],
            "indices": [0, 0],
        }
        for block, values in (("sequences", sequences), ("interfaces", interfaces))
        for key, value in values.items()
    ]
    raw["columns"] = [raw["columns"][0], *columns, raw["columns"][1]]
    answer = {
        "snapshot_digest": raw["snapshot_digest"],
        "paths": [
            {
                "materialized_realization_id": identity,
                "values": {"left_gap": gap, "release_method": "enzyme-a"},
            }
            for identity, gap in (("A", 0), ("B", 4))
        ],
        "axes": [{"key": "release_method", "nodes": [{"value": "enzyme-a", "label": "Enzyme A"}]}],
    }
    return raw, answer, descriptors


def test_json_sequence_lists_and_nested_contacts_match_typed_tuples(complete_binding):
    from hop_design.design.construction.editions.overview import validate_overview

    raw, answer, descriptors = complete_binding
    overview = PreparationOverview.model_validate_json(json.dumps(raw))
    assert descriptors["A"].sequences["loop"] == ("A", "C")
    assert descriptors["A"].sequences["basal_pairs"] == (("A", "T", "watson_crick"),)
    assert next(c for c in overview.columns if c.key == "sequences.loop").dictionary == (
        ["A", "C"],
    )
    before = overview.model_dump(mode="json")
    validate_overview(overview, answer, descriptors)
    assert overview.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "key,value",
    [
        ("shape.left_gap", "0"),
        ("sequences.loop", ["A", "G"]),
        ("sequences.loop", "AC"),
        ("sequences.loop", ["A", ["C"]]),
        ("sequences.basal_pairs", [["T", "A", "watson_crick"]]),
        ("sequences.basal_pairs", [["A", "T", "wobble"]]),
        ("sequences.foldback_pairs", [["A", "T", "watson_crick"]]),
        ("sequences.foldback_pairs", [["G", "C", "watson_crick"], ["A", "T", "watson_crick"]]),
        ("interfaces.left_word", "AACC"),
        ("interfaces.left_polarity", "three_prime"),
        ("processing.release_method", "enzyme-b"),
    ],
)
def test_corrupt_values_in_every_comparison_block_reject(complete_binding, key, value):
    from hop_design.design.construction.editions.overview import validate_overview

    raw, answer, descriptors = complete_binding
    column = next(c for c in raw["columns"] if c["key"] == key)
    column["dictionary"][0] = value
    overview = PreparationOverview.model_validate_json(json.dumps(raw))
    with pytest.raises(ValueError, match="feature value"):
        validate_overview(overview, answer, descriptors)


def test_sequence_binding_requires_each_captured_descriptor(complete_binding):
    from hop_design.design.construction.editions.overview import validate_overview

    raw, answer, descriptors = complete_binding
    descriptors.pop("B")
    overview = PreparationOverview.model_validate_json(json.dumps(raw))
    with pytest.raises(ValueError, match="needs the captured molecular descriptor"):
        validate_overview(overview, answer, descriptors)


def test_empty_contact_lists_match_empty_typed_contact_tuples(complete_binding):
    from hop_design.design.construction.editions.overview import validate_overview

    raw, answer, descriptors = complete_binding
    next(c for c in raw["columns"] if c["key"] == "sequences.basal_pairs")["dictionary"] = [[]]
    for identity, descriptor in descriptors.items():
        value = descriptor.model_dump()
        value["sequences"]["basal_pairs"] = ()
        value["shape"]["open_side_paired_positions"] = 0
        descriptors[identity] = type(descriptor).model_validate(value)
    overview = PreparationOverview.model_validate_json(json.dumps(raw))
    validate_overview(overview, answer, descriptors)


def test_missing_processing_value_is_not_admitted(complete_binding):
    from hop_design.design.construction.editions.overview import validate_overview

    raw, answer, descriptors = complete_binding
    del answer["paths"][0]["values"]["release_method"]
    overview = PreparationOverview.model_validate_json(json.dumps(raw))
    with pytest.raises(KeyError, match="release_method"):
        validate_overview(overview, answer, descriptors)


@pytest.mark.parametrize(
    "fault,message",
    [
        ("snapshot", "snapshot or preparation membership"),
        ("membership", "snapshot or preparation membership"),
        ("scale", "observed-range scale"),
        ("label", "display name"),
    ],
)
def test_binding_preserves_snapshot_membership_scale_and_label_checks(
    complete_binding, fault, message
):
    from hop_design.design.construction.editions.overview import validate_overview

    raw, answer, descriptors = complete_binding
    if fault == "snapshot":
        answer["snapshot_digest"] = "sha256:" + "c" * 64
    elif fault == "membership":
        answer["paths"].pop()
    elif fault == "scale":
        raw["basis"]["shape_scales"]["left_gap"] = 8
    else:
        raw["columns"][-1]["display_dictionary"][0] = "Wrong enzyme name"
    overview = PreparationOverview.model_validate_json(json.dumps(raw))
    with pytest.raises(ValueError, match=message):
        validate_overview(overview, answer, descriptors)


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


def test_current_presentation_updates_saved_labels_without_changing_the_record():
    from hop_design.export.construction.survey.recorded_overview import comparison_packet

    overview = PreparationOverview.model_validate_json(json.dumps(document()))
    original = overview.model_dump(mode="json")
    packet = comparison_packet(overview, overview.members)
    assert packet["columns"][0]["label"] == "Left insert spacer"
    assert "Excludes the sticky-end bases" in packet["columns"][0]["definition"]
    for captured, displayed in zip(original["columns"], packet["columns"], strict=True):
        scientific = {k: v for k, v in displayed.items() if k not in {"label", "definition"}}
        assert scientific == {k: v for k, v in captured.items() if v is not None and k != "label"}
    assert overview.model_dump(mode="json") == original
