"""
--------------------------------------------------------------------------------
HOP Design
hop-design/tests/unit/test_comparison_glyphs.py

Keep schematic comparison glyphs independent of values and comparison order.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import copy
import itertools
import json
from math import cos, radians, sin
from xml.etree import ElementTree as ET

from hop_design.export.construction.molecular.primitives.typography import text_width
from hop_design.export.construction.presentation.comparison_glyphs import (
    comparison_glyph_presentation,
)
from hop_design.export.construction.survey.comparison_vector import render_comparison_vector

FIELDS = (
    "shape.left_gap",
    "shape.loop_nt",
    "shape.loop_side_paired_bp",
    "shape.open_side_paired_positions",
    "shape.right_gap",
    "sequences.basal_pairs",
    "sequences.foldback_pairs",
    "sequences.loop",
    "interfaces.left_word",
    "interfaces.right_word",
    "processing.basal_method",
    "processing.foldback_method",
    "processing.release_method",
)


def packet(keys=FIELDS):
    fields = [
        {
            "key": key,
            "label": key.split(".")[1],
            "unit": "",
            "display_value": i,
            "encoded": ["A", "T"] if key.startswith("sequences.") else i,
            "value": i,
            "active": True,
            "parameters": [key.split(".")[1]],
        }
        for i, key in enumerate(keys)
    ]
    return {
        "identity": "preparation-example",
        "basis": {"unaltered": True},
        "presentation": {**comparison_glyph_presentation(keys), "groups": {}},
        "vector": fields,
    }


def test_reviewed_display_order_does_not_reorder_the_comparison_vector():
    source = packet()
    before = copy.deepcopy(source)
    root = ET.fromstring(render_comparison_vector(source))
    assert source == before
    expected = [FIELDS[i] for i in (3, 2, 1, 0, 4, 5, 6, 7, 8, 9, 10, 11, 12)]
    assert [n.get("data-feature") for n in root.iter() if n.get("data-feature")] == expected
    assert json.loads(next(n.text for n in root if n.tag.endswith("metadata"))) == source
    assert root.get("data-comparison-display") == "schematic-glyphs"
    assert not any(n.get("data-display-value") for n in root.iter())
    assert all(
        n.get("tabindex") == "0" and json.loads(n.get("aria-label"))["key"] == n.get("data-feature")
        for n in root.iter()
        if n.get("data-feature")
    )
    labels = [n for n in root.iter() if n.get("data-feature-label")]
    assert all(n.get("font-size") == "7.2" for n in labels)
    assert all(n.get("transform").startswith("rotate(-45 ") for n in labels)
    positions = [float(n.get("data-display-x")) for n in root.iter() if n.get("data-feature")]
    assert all(abs(b - a - 13.2) < 1e-9 for a, b in itertools.pairwise(positions))


def test_schematic_geometry_identifies_field_type_without_encoding_selected_values():
    source = packet()
    changed = copy.deepcopy(source)
    for field in changed["vector"]:
        field.update(display_value=987, value="different", encoded=["C", "G"])
    first, second = (ET.fromstring(render_comparison_vector(p)) for p in (source, changed))

    def glyphs(root):
        return [ET.tostring(n) for n in root.iter() if n.get("data-input-glyph")]

    assert len(glyphs(first)) == len(FIELDS)
    assert glyphs(first) == glyphs(second)
    assert all(n.find("{*}title") is not None for n in first.iter() if n.get("data-feature"))
    shapes = source["presentation"]["glyphs"]
    assert shapes["shape.left_gap"] != shapes["shape.right_gap"]
    assert shapes["processing.release_method"] != shapes["processing.basal_method"]


def test_other_fieldsets_keep_tails_polarity_and_unknown_inputs_visible():
    keys = (
        "shape.five_prime_retained_tail_nt",
        "sequences.three_prime_retained_tail",
        "interfaces.left_polarity",
        "processing.new_method",
    )
    source = packet(keys)
    root = ET.fromstring(render_comparison_vector(source))
    assert len([n for n in root.iter() if n.get("data-input-glyph")]) == len(keys)
    assert set(source["presentation"]["display_order"]) == set(keys)
    assert all(source["presentation"]["glyphs"][key]["nodes"] for key in keys)


def test_static_rotated_labels_stay_inside_the_compact_figure():
    source = packet()
    source["vector"][3]["label"] = "Basal contact positions outside the supplied fixed stem"
    root = ET.fromstring(render_comparison_vector(source))
    width, height = (float(root.get("viewBox").split()[i]) for i in (2, 3))
    for label in (n for n in root.iter() if n.get("data-feature-label")):
        reach = text_width(label.text, 7.2) * 0.707
        assert float(label.get("x")) - reach >= 2
        assert float(label.get("x")) + 7.2 * 0.707 < width
        assert float(label.get("y")) + reach < height


def test_static_typography_and_bounds_follow_shared_presentation_metadata():
    source = packet()
    source["vector"][3]["label"] = "Basal contact positions outside the supplied fixed stem"
    default = ET.fromstring(render_comparison_vector(source))
    source["presentation"].update(font_size=8, field_pitch=15, label_angle=-30)
    root = ET.fromstring(render_comparison_vector(source))
    labels = [n for n in root.iter() if n.get("data-feature-label")]
    assert all(float(n.get("font-size")) == 8 for n in labels)
    assert all(n.get("transform").startswith("rotate(-30 ") for n in labels)
    fields = [n for n in root.iter() if n.get("data-feature")]
    assert all(
        abs(float(b.get("data-display-x")) - float(a.get("data-display-x")) - 15) < 1e-9
        for a, b in itertools.pairwise(fields)
    )
    width, height = (float(root.get("viewBox").split()[i]) for i in (2, 3))
    assert width != float(default.get("viewBox").split()[2])
    assert height != float(default.get("viewBox").split()[3])
    for label in labels:
        assert (
            float(label.get("x"))
            - text_width(label.text, 8) * cos(radians(30))
            - 8 * sin(radians(30))
            >= 2 - 1e-9
        )
        assert float(label.get("y")) + text_width(label.text, 8) * sin(radians(30)) < height


def test_reviewed_fixed_stem_and_spacer_context_rails_have_butt_linecaps():
    root = ET.fromstring(render_comparison_vector(packet()))
    fixed = [n for n in root.iter() if n.get("data-fixed-stem")]
    context = [n for n in root.iter() if n.get("data-end-context")]
    assert len(fixed) == 4 and len(context) == 2
    assert all(
        n.get("stroke-linecap") == "butt"
        for group in fixed
        for n in group
        if n.tag.endswith("line")
    )
    assert all(n.get("stroke-linecap") == "butt" for n in context)
