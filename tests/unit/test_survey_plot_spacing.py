"""Wide sequence labels need more horizontal space than short numeric nodes."""

from itertools import pairwise

from hop_design.export.construction.molecular.primitives.typography import text_width
from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
from hop_design.export.construction.survey.layout import FONT, WIDTH, node_geometry, plot_axes
from hop_design.models.construction.variants.parameters import parameter_definition


def test_mixed_axes_fit_without_adjacent_sequence_labels_colliding():
    axes = [
        {
            "symbol": "p",
            "kind": "categorical",
            "representation": "sequence",
            "unit": "nt",
            "nodes": [
                {
                    "value": "ACGT" if i % 3 else "1",
                    "label": "ACGT" if i % 3 else "1",
                    "supported_preparations": 1,
                }
            ],
        }
        for i in range(27)
    ]
    plotted = plot_axes({"axes": axes})
    half = [max(18, len(a["nodes"][0]["label"]) * FONT * 0.56 + 4) / 2 for a in axes]
    for (left, lh), (right, rh) in pairwise(zip(plotted, half, strict=True)):
        if left["band"] == right["band"]:
            assert right["x"] - rh >= left["x"] + lh + 6 - 1e-9
    assert len({p["band"] for p in plotted}) > 1
    assert plotted[0]["x"] - half[0] >= 0
    assert plotted[-1]["x"] + half[-1] <= WIDTH
    assert plot_axes({"axes": axes, "query": {"parameters": [{"key": "ignored"}]}}) == plotted


def test_primary_molecular_choices_keep_methods_on_the_same_connected_row():
    labels = [
        ("Basal nickase", "Nb.BsrDI", ""),
        ("5\u2032 tail", "17", "nt"),
        ("Loop-side extension", "8", "bp"),
        ("Loop size", "6", "nt"),
        ("Loop sequence", "AAAACG", ""),
        ("Left sticky end", "AAAA", ""),
        ("Left gap", "6", "bp"),
        ("Right sticky end", "AAAC", ""),
        ("Right gap", "6", "bp"),
        ("Release enzyme", "BsmBI-v2", ""),
    ]
    axes = [
        {
            "label": label,
            "symbol": "",
            "kind": "categorical",
            "representation": "sequence",
            "unit": unit,
            "nodes": [{"value": value, "label": value, "supported_preparations": 1}],
        }
        for label, value, unit in labels
    ]
    plotted = plot_axes({"axes": axes})
    assert {a["band"] for a in plotted} == {0}
    for left, right in pairwise(plotted):
        assert right["x"] - right["width"] / 2 >= left["x"] + left["width"] / 2 + 6


def test_narrow_region_heading_fits_a_single_interface_axis():
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.molecular.primitives.typography import text_width
    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
    from hop_design.export.construction.survey.plot import render_survey_plot
    from tests.unit.test_survey_plot import choices

    answer = choices()
    answer["axes"] = [a for a in answer["axes"] if a["key"] == "left_end_word"]
    root = ET.fromstring(render_survey_plot(answer, profile=INSPECTOR_FIGURE))
    children = list(root)
    band = next(e for e in children if e.get("data-axis-region"))
    headings = []
    for e in children[children.index(band) + 1 :]:
        if not e.tag.endswith("}text"):
            break
        headings.append(e)
    assert " ".join(e.text for e in headings) == "Released insert"
    left, right = float(band.get("x")), float(band.get("x")) + float(band.get("width"))
    for heading in headings:
        x = float(heading.get("x"))
        width = text_width(heading.text, INSPECTOR_FIGURE.axis_font)
        assert x - width / 2 >= left
        assert x + width / 2 <= right


def test_seven_molecular_features_remain_one_connected_inspector_row():
    keys = (
        "open_side_paired_positions",
        "left_end_word",
        "left_gap",
        "right_gap",
        "right_end_word",
        "foldback_arm_bp",
        "loop_nt",
    )
    axes = []
    for key in keys:
        definition = parameter_definition(key).model_dump(mode="json")
        value = "GGGG" if key.endswith("word") else 15
        axes.append(
            {
                **definition,
                "nodes": [{"value": value, "label": str(value), "supported_preparations": 1}],
            }
        )
    plotted = plot_axes({"axes": axes}, profile=INSPECTOR_FIGURE)
    assert [a["definition"]["key"] for a in plotted] == list(keys)
    assert {a["band"] for a in plotted} == {0}
    assert INSPECTOR_FIGURE.axis_font >= 19


def test_sticky_word_contour_contains_actual_type_bounds():
    axis = parameter_definition("left_end_word").model_dump(mode="json")
    node = {"label": "GGGG", "value": "GGGG"}
    contour = node_geometry(axis, node, profile=INSPECTOR_FIGURE)
    assert contour["width"] >= text_width("GGGG", INSPECTOR_FIGURE.axis_font) + 4


def test_wrapped_axes_use_balanced_rows_without_changing_reading_order():
    from collections import Counter

    axes = [
        {
            "key": f"axis_{index}",
            "label": "Loop-side extension",
            "symbol": "A",
            "kind": "numeric",
            "representation": "span",
            "unit": "bp",
            "neighborhood": "closing",
            "nodes": [{"value": 6, "label": "6", "supported_preparations": 1}],
        }
        for index in range(13)
    ]
    plotted = plot_axes({"axes": axes})
    counts = Counter(axis["band"] for axis in plotted)
    assert len(counts) == 2
    assert max(counts.values()) - min(counts.values()) <= 1
    assert [axis["definition"] for axis in plotted] == axes
    for left, right in pairwise(plotted):
        if left["band"] == right["band"]:
            assert right["x"] - right["width"] / 2 >= left["x"] + left["width"] / 2 + 6


def test_recognition_name_does_not_wrap_a_single_character_suffix():
    axis = parameter_definition("foldback_method").model_dump(mode="json")
    node = {"label": "Nt.Bpu10I", "value": "example:enzyme/nt.bpu10i@1"}
    contour = node_geometry(axis, node)
    assert contour["lines"] == ["Nt.Bpu10I"]
