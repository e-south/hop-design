"""One measured composition drives exported and interactive teaching figures."""

import json
from dataclasses import replace
from io import BytesIO
from xml.etree import ElementTree as ET

import pytest
from reportlab.graphics.shapes import String, mmult, transformPoint
from svglib.svglib import svg2rlg

from hop_design.export.construction.presentation.figure_profile import PUBLICATION_FIGURE
from hop_design.export.construction.survey.figure import compose_figure
from hop_design.export.construction.survey.figure_layout import (
    figure_layout,
    plot_geometry,
    teaching_geometry,
)

KEY = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1008 280">
<g data-parameter-anchor="loop_word" data-anchor-box="[800,100,40,30]"/>
</svg>"""
PLOT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 700"
data-landscape-frame="0 0 1200 660"><g data-axis="loop_word" data-band="0">
<g data-axis-title="loop_word"><text x="600" y="66">Loop</text></g></g></svg>"""


def test_pdf_panel_positions_agree_with_root_connector_coordinates():
    drawing = ET.fromstring(compose_figure(KEY, PLOT, {"axes": []}))
    spec = json.loads(drawing.get("data-figure-layout"))
    # A marker in page coordinates must coincide with the axis label inside its panel.
    marker = ET.SubElement(
        drawing, "{http://www.w3.org/2000/svg}text", {"x": "600", "y": str(spec["trace"]["y"] + 66)}
    )
    marker.text = "coordinate-control"
    converted = svg2rlg(BytesIO(ET.tostring(drawing)))
    positions = {}

    def visit(shape, parent=(1, 0, 0, 1, 0, 0)):
        matrix = mmult(parent, getattr(shape, "transform", (1, 0, 0, 1, 0, 0)))
        if isinstance(shape, String):
            positions[shape.text] = transformPoint(matrix, (shape.x, shape.y))
        for child in getattr(shape, "contents", ()):
            visit(child, matrix)

    visit(converted)
    assert positions["Loop"] == pytest.approx(positions["coordinate-control"])


def test_browser_spec_and_export_share_transforms_and_connectors():
    expected = figure_layout(teaching_geometry(KEY), plot_geometry(PLOT))
    exported = ET.fromstring(compose_figure(KEY, PLOT, {"axes": []}))
    assert json.loads(exported.attrib["data-figure-layout"]) == expected
    panels = [e for e in exported if e.get("data-figure-panel")]
    assert [e.get("data-figure-panel") for e in panels] == ["hairpin", "trace"]
    for name, panel in zip(("hairpin", "trace"), panels, strict=True):
        box = expected[name]
        assert panel.attrib["data-panel-frame"] == box["frame"]
        assert panel.attrib["transform"].startswith(f"translate({box['x']} {box['y']}) ")
    polygon = next(e for e in exported.iter() if e.tag.endswith("}polygon"))
    assert polygon.attrib["points"] == expected["links"][0]["points"]


@pytest.mark.parametrize("profile", [PUBLICATION_FIGURE, replace(PUBLICATION_FIGURE, axis_font=35)])
def test_curated_figure_uses_complete_drawing_frame_without_moving_browser_slots(profile):
    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE

    key = KEY.replace(b"viewBox=", b'data-content-frame="40 -10 840 300" viewBox=')
    plot = PLOT.replace(
        b"<g data-axis=", b'<metadata data-display-projection="true"/><g data-axis='
    )
    static = ET.fromstring(compose_figure(key, plot, {"axes": []}, profile=profile))
    layout = json.loads(static.get("data-figure-layout"))
    assert layout["hairpin"]["frame"] == "40 -10 840 300"
    assert layout["hairpin"]["height"] == pytest.approx(300 * 1200 / 840)
    fan = next(e for e in static.iter() if e.tag.endswith("}polygon"))
    first_x = float(fan.get("points").split()[0].split(",")[0])
    assert first_x == pytest.approx((800 - 40) * 1200 / 840)

    interactive = ET.fromstring(compose_figure(key, plot, {"axes": []}, profile=INSPECTOR_FIGURE))
    assert json.loads(interactive.get("data-figure-layout"))["hairpin"]["frame"] == "0 0 1008 280"


def test_connectors_stop_before_category_bands_and_axis_titles():
    spec = figure_layout(teaching_geometry(KEY), plot_geometry(PLOT))
    for link in spec["links"]:
        bottom = [float(point.split(",")[1]) for point in link["points"].split()[2:]]
        assert max(bottom) <= spec["trace"]["y"]


def test_column_detail_reserves_a_panel_letter_between_molecule_and_trace():
    from hop_design.export.construction.presentation.figure_profile import LANDSCAPE_DETAIL_FIGURE

    # At half of a seven-inch plate, a 10 pt panel letter needs clearance from
    # the last measured molecular annotation. Browser slots have no panel letter.
    profile = replace(LANDSCAPE_DETAIL_FIGURE, minimum_teaching_slot=0, teaching_slot_step=1)
    spec = figure_layout(teaching_geometry(KEY), plot_geometry(PLOT), profile=profile)
    molecule_bottom = spec["hairpin"]["y"] + spec["hairpin"]["height"]
    printed_gap = (spec["trace"]["y"] - molecule_bottom) * 246 / profile.width
    assert printed_gap >= 13


def test_teaching_slot_is_stable_but_long_molecules_get_continuation_room():
    plot = plot_geometry(PLOT)
    first = figure_layout(teaching_geometry(KEY), plot)
    shorter = figure_layout(teaching_geometry(KEY.replace(b"1008 280", b"1008 230")), plot)
    longer = figure_layout(teaching_geometry(KEY.replace(b"1008 280", b"1008 600")), plot)
    assert first["trace"]["y"] == shorter["trace"]["y"] == 372
    assert longer["trace"]["y"] > first["trace"]["y"]
    assert longer["hairpin"]["width"] == first["hairpin"]["width"] == 1200


def test_no_varying_axes_has_the_same_positive_frame_in_export_and_browser():
    from hop_design.export.construction.survey.plot import render_survey_plot
    from hop_design.export.construction.survey.traces import TraceProjection
    from tests.unit.test_survey_plot import choices

    answer = choices()
    answer["axes"] = []
    for path in answer["paths"]:
        path["values"] = {}
    drawing = render_survey_plot(answer)
    projection = TraceProjection(answer)
    assert plot_geometry(drawing)["frame"] == projection.frame
    assert float(projection.frame.split()[3]) > 0


def test_narrow_figure_export_and_inspection_share_profile_and_inherited_type():
    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE

    key = KEY.replace(b"viewBox=", b'font-size="32" viewBox=')
    plot = PLOT.replace(b"viewBox=", b'font-size="18" viewBox=')
    expected = figure_layout(teaching_geometry(key), plot_geometry(plot), profile=INSPECTOR_FIGURE)
    drawing = ET.fromstring(compose_figure(key, plot, {"axes": []}, profile=INSPECTOR_FIGURE))
    assert float(expected["frame"].split()[2]) == 600
    assert json.loads(drawing.get("data-figure-layout")) == expected
    panels = [e for e in drawing if e.get("data-figure-panel")]
    assert [p.get("font-size") for p in panels] == ["32", "18"]


def test_curated_plate_and_trace_share_axes_without_losing_preparations():
    from copy import deepcopy

    from hop_design.export.construction.survey.plot import render_survey_plot
    from hop_design.export.construction.survey.traces import TraceProjection
    from tests.unit.test_survey_plot import choices

    answer = choices()
    other = deepcopy(answer["paths"][0])
    other["materialized_realization_id"] = "different-loop"
    other["values"]["loop_nt"] = 6
    answer["paths"].append(other)
    axes = ("left_gap", "right_gap", "foldback_arm_bp", "release_method")
    plot = render_survey_plot(answer, selected_identity="different-loop", display_axes=axes)
    projection = TraceProjection(answer, display_axes=axes)
    assert [v["key"] for v in projection.trace("different-loop")["values"]] == list(axes)
    assert projection.projection != TraceProjection(answer).projection
    assert projection.trace("exact-one")["path"] == projection.trace("different-loop")["path"]
    drawing = ET.fromstring(plot)
    members = [json.loads(e.get("data-members")) for e in drawing.iter() if e.get("data-members")]
    assert members == [["exact-one", "different-loop"]]
    receipt = json.loads(next(e.text for e in drawing.iter() if e.get("data-display-projection")))
    assert receipt["displayed"] == list(axes) and "loop_nt" in receipt["omitted"]
    assert plot_geometry(plot)["frame"] == projection.frame
    figure = ET.fromstring(compose_figure(KEY, plot, answer, selected_identity="different-loop"))
    width, height = map(float, figure.get("viewBox").split()[2:])
    assert height / width <= 4.5 / 7
    assert float(drawing.get("font-size")) * 504 / width >= 8
