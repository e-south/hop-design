"""Measured type remains clear of values and neighboring continuation bands."""

import re
from dataclasses import replace
from xml.etree import ElementTree as ET

import pytest

from hop_design.export.construction.presentation.figure_profile import (
    INSPECTOR_FIGURE,
    PUBLICATION_FIGURE,
)
from hop_design.export.construction.survey.figure_layout import plot_geometry
from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.export.construction.survey.traces import TraceProjection
from tests.unit.test_survey_plot import choices


def test_inspector_labels_are_regular_45_degree_runs_below_the_axes():
    records = choices()
    root = ET.fromstring(render_survey_plot(records, profile=INSPECTOR_FIGURE))
    frame = __import__("json").loads(root.get("data-axis-frame"))
    headings = [e for e in root.iter() if e.get("data-heading-angle")]
    assert headings
    assert all(e.get("data-heading-angle") == "-45" for e in headings)
    assert all(float(e.get("y")) > frame["bottom"] for e in headings)
    assert all(e.get("font-weight") == "normal" for e in headings)
    axes = [e for e in root if e.get("data-axis-line")]
    assert len(axes) == len(headings)
    assert {e.get("stroke") for e in axes} == {"#465459"}
    assert all(float(e.get("stroke-width")) <= 1 for e in axes)


def test_adjacent_rotated_headings_have_room_for_their_full_line_height():
    from itertools import pairwise
    from math import sqrt

    from hop_design.export.construction.survey.layout import plot_layout

    layout = plot_layout(choices(), profile=INSPECTOR_FIGURE)
    for a, b in pairwise(layout.axes):
        # Parallel 45-degree text lines need their font height perpendicular
        # to the baseline, even when adjacent axes contain one-digit values.
        assert (b["x"] - a["x"]) / sqrt(2) >= INSPECTOR_FIGURE.axis_font * 1.2 + 2


def test_publication_axes_remain_readable_in_a_full_width_trace():
    from hop_design.export.construction.presentation.figure_profile import LANDSCAPE_DETAIL_FIGURE

    drawing = ET.fromstring(
        render_survey_plot(
            choices(), selected_identity="exact-one", profile=LANDSCAPE_DETAIL_FIGURE
        )
    )
    # The selected trace uses the seven-inch plate width.
    width = float(drawing.get("data-landscape-frame").split()[2])
    assert float(drawing.get("font-size")) * 498 / width >= 7


@pytest.mark.parametrize("profile", [INSPECTOR_FIGURE, replace(PUBLICATION_FIGURE, axis_font=35)])
def test_measured_headings_clear_values_and_retain_exact_overlay(profile):
    records = choices()
    # Detailed axes exercise continuation rows as well as wrapped headings.
    for axis in records["axes"]:
        axis["domain"] = {"basis": "observed_only"}
    records["query"]["parameters"] = [
        {"key": axis["key"], "values": [axis["nodes"][0]["value"]]} for axis in records["axes"]
    ]
    drawing = ET.fromstring(
        render_survey_plot(records, profile=profile, selected_identity="exact-one")
    )
    font = float(drawing.get("font-size"))
    axes = [element for element in drawing if element.get("data-axis")]
    assert (
        len({axis.get("data-band") for axis in axes}) == 1
        if profile.single_row
        else len({axis.get("data-band") for axis in axes}) > 1
    )
    bottom_by_band = {}
    top_by_band = {}
    for axis in axes:
        title = next(element for element in axis if element.get("data-axis-title"))
        text = [element for element in title if element.tag.endswith("}text")]

        def bottom(element):
            rotation = re.fullmatch(r"rotate\(-90 [^ ]+ ([^)]+)\)", element.get("transform", ""))
            # A start-anchored -90-degree text run ends at the rotation origin;
            # its untransformed y attribute describes the perpendicular baseline.
            return float(rotation.group(1)) if rotation else float(element.get("y")) + font * 0.25

        title_bottom = max(bottom(element) for element in text)
        labels = [
            element
            for element in axis.iter()
            if element.tag.endswith("}rect") and element.get("data-node-label")
        ]
        assert labels
        if profile.rotated_labels:
            assert max(float(e.get("y")) + float(e.get("height")) for e in labels) + 6 <= min(
                float(e.get("y")) for e in text
            )
        else:
            assert min(float(element.get("y")) for element in labels) >= title_bottom + 6
        band = int(axis.get("data-band"))
        top_by_band[band] = min(
            top_by_band.get(band, float("inf")),
            min(float(element.get("y")) - font for element in text),
        )
        bottom_by_band[band] = max(
            bottom_by_band.get(band, 0),
            max(float(element.get("y")) + float(element.get("height")) for element in labels),
        )
    for band in sorted(bottom_by_band)[:-1]:
        assert bottom_by_band[band] + 6 <= top_by_band[band + 1]
    frame_height = float(drawing.get("data-landscape-frame").split()[3])
    assert max(bottom_by_band.values()) <= frame_height - 6
    projection = TraceProjection(records, profile=profile)
    assert plot_geometry(drawing) == projection.figure_geometry
    selected = next(e for e in drawing.iter() if e.get("data-selected") == "true")
    assert projection.trace("exact-one")["path"] == selected.get("d")
