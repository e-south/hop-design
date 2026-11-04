"""One exact overlay uses the same full-domain coordinates as publication paths."""

import copy
import json
from xml.etree import ElementTree as ET

import pytest

from hop_design.export.construction.survey.plot import render_survey_plot
from tests.unit.test_survey_plot import choices


def test_inspector_profile_keeps_exact_paths_with_readable_annotation_scale():
    from dataclasses import replace

    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
    from hop_design.export.construction.survey.figure_layout import plot_geometry
    from hop_design.export.construction.survey.traces import TraceProjection

    records = choices()
    narrow = TraceProjection(records, profile=INSPECTOR_FIGURE)
    public = TraceProjection(records)
    tree = ET.fromstring(
        render_survey_plot(records, selected_identity="exact-one", profile=INSPECTOR_FIGURE)
    )
    assert float(tree.get("font-size")) * 412 / float(narrow.frame.split()[2]) >= 12
    assert float(narrow.frame.split()[2]) == 600
    assert plot_geometry(tree) == narrow.figure_geometry
    path = next(e for e in tree.iter() if e.get("data-selected") == "true")
    assert narrow.trace("exact-one")["path"] == path.get("d")
    assert [(v["key"], v["value"]) for v in narrow.trace("exact-one")["values"]] == [
        (v["key"], v["value"]) for v in public.trace("exact-one")["values"]
    ]
    assert narrow.projection != public.projection
    renamed = TraceProjection(records, profile=replace(INSPECTOR_FIGURE, key="test-layout/v2"))
    assert renamed.frame == narrow.frame and renamed.projection != narrow.projection


def test_overlay_preserves_grouped_identity_band_breaks_and_exact_selected_values():
    from hop_design.export.construction.survey.traces import TraceProjection

    records = choices()
    # Explicitly inspecting the detailed coordinates requires continuation bands.
    for axis in records["axes"]:
        axis["domain"] = {"basis": "observed_only"}
    records["query"]["parameters"] = [
        {"key": axis["key"], "values": [axis["nodes"][0]["value"]]} for axis in records["axes"]
    ]
    first = records["paths"][0]
    records["paths"].append({**first, "materialized_realization_id": "exact-two", "matches": False})
    projection = TraceProjection(records)
    svg = ET.fromstring(render_survey_plot(records, selected_identity="exact-two"))
    expected = next(e for e in svg.iter() if e.get("data-selected") == "true")
    overlay = projection.trace("exact-two")
    assert overlay["path"] == expected.get("d")
    assert overlay["materialized_realization_id"] == "exact-two"
    assert overlay["eligible"] is False
    assert set(json.loads(expected.get("data-members"))) == {"exact-one", "exact-two"}
    assert overlay["path"].count("M") > 1
    end = next(v for v in overlay["values"] if v["key"] == "left_end_word")
    assert end["value"] == "TGCA" and end["label"] == "Left sticky end"
    with pytest.raises(ValueError, match="recorded"):
        projection.trace("absent")


def test_eligibility_changes_do_not_move_coordinates_or_mutate_a_prior_overlay():
    from hop_design.export.construction.survey.traces import TraceProjection

    records = choices()
    first = TraceProjection(records).trace("exact-one")
    filtered = copy.deepcopy(records)
    filtered["query"]["parameters"] = [{"key": "left_end_word", "values": ["AAAA"]}]
    filtered["paths"][0]["matches"] = False
    second = TraceProjection(filtered).trace("exact-one")
    assert first["path"] == second["path"]
    assert first["eligible"] and not second["eligible"]
    assert first["projection"] == second["projection"]


@pytest.mark.parametrize(
    ("method_label", "expected_lines"),
    [("Nb.Mva1269I", ["Nb.Mva1269I"]), ("BsaI-HFv2", ["BsaI-", "HFv2"])],
)
def test_overlay_label_geometry_matches_the_static_figure_for_method_names(
    method_label, expected_lines
):
    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
    from hop_design.export.construction.survey.traces import TraceProjection

    records = choices()
    method = next(a for a in records["axes"] if a["key"] == "release_method")
    method["domain"]["values"] = ["method-one", "method-two"]
    method["nodes"] = [
        {**method["nodes"][0], "value": value, "label": label}
        for value, label in (("method-one", method_label), ("method-two", "BsaI-HFv2"))
    ]
    records["paths"][0]["values"]["release_method"] = "method-one"
    svg = ET.fromstring(
        render_survey_plot(records, selected_identity="exact-one", profile=INSPECTOR_FIGURE)
    )
    axis = next(e for e in svg.iter() if e.get("data-axis") == "release_method")
    node = next(e for e in axis if e.get("data-node-value") == '"method-one"')
    box = next(e for e in node if e.tag.endswith("}rect"))
    lines = [e.text for e in node if e.tag.endswith("}text")]
    assert lines == expected_lines and "".join(lines) == method_label
    trace = TraceProjection(records, profile=INSPECTOR_FIGURE).trace("exact-one")
    label = next(v for v in trace["values"] if v["key"] == "release_method")
    assert label["node_label"] == {
        "lines": lines,
        "width": float(box.attrib["width"]),
        "height": float(box.attrib["height"]),
    }


def test_projection_binds_node_labels_without_moving_coordinates():
    from hop_design.export.construction.survey.traces import TraceProjection

    records = choices()
    before = TraceProjection(records)
    records = copy.deepcopy(records)
    for axis in records["axes"]:
        if axis["key"] == "left_end_word":
            for node in axis["nodes"]:
                node["label"] = node["label"].replace("TGCA", "TGCT")
    after = TraceProjection(records)
    assert before.trace("exact-one")["values"] != after.trace("exact-one")["values"]
    assert before.trace("exact-one")["path"] == after.trace("exact-one")["path"]
    assert before.projection != after.projection
