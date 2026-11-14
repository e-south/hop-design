"""Column details keep every scientific coordinate and exact feature record."""

import json
from xml.etree import ElementTree as ET

import pytest

from hop_design.export.construction.presentation.comparison import COMPARISON_GROUPS


def display_packet(packet):
    packet["presentation"] = {"groups": COMPARISON_GROUPS}
    for field in packet["vector"]:
        field["display_value"] = field["value"] if field["key"].startswith("shape.") else 0
    return packet


def test_column_trace_preserves_twelve_axes_at_readable_physical_type():
    from hop_design.export.construction.presentation.figure_profile import COLUMN_DETAIL_FIGURE
    from hop_design.export.construction.survey.layout import plot_axes

    labels = [
        ("Basal nickase", "Nb.BssSI", "recognition"),
        ("Foldback nickase", "Nt.Bpu10I", "recognition"),
        ("Release enzyme", "BsaI-HFv2", "recognition"),
        ("Loop sequence", "AAAACG", "sequence"),
        ("Left sticky end", "CGAG", "sequence"),
        ("Right sticky end", "CAAG", "sequence"),
        ("Left gap", "0", "span"),
        ("Right gap", "0", "span"),
        ("Loop size", "4", "span"),
        ("Loop-side extension", "6", "span"),
        ("Join offset", "2", "span"),
        ("Basal paired extent", "18", "span"),
    ]
    keys = [
        "basal_method",
        "foldback_method",
        "release_method",
        "loop_word",
        "left_end_word",
        "right_end_word",
        "left_gap",
        "right_gap",
        "loop_nt",
        "foldback_arm_bp",
        "join_offset_nt",
        "open_side_paired_positions",
    ]
    axes = [
        {
            "key": keys[i],
            "label": label,
            "symbol": str(i),
            "kind": "categorical" if kind in {"recognition", "sequence"} else "numeric",
            "representation": kind,
            "unit": "",
            "nodes": [{"value": value, "label": value, "supported_preparations": 1}],
        }
        for i, (label, value, kind) in enumerate(labels)
    ]
    from hop_design.export.construction.presentation.figure_profile import column_detail_profile

    # Full stage-qualified names retain the font and need an explicit wider budget.
    with pytest.raises(ValueError, match=r"at least .* points for readable labels"):
        plot_axes({"axes": axes}, profile=COLUMN_DETAIL_FIGURE)
    profile = column_detail_profile(266)
    plotted = plot_axes({"axes": axes}, profile=profile)
    assert [p["definition"]["key"] for p in plotted] == [a["key"] for a in axes]
    assert {p["band"] for p in plotted} == {0}
    assert profile.axis_font == COLUMN_DETAIL_FIGURE.axis_font
    assert profile.axis_font * profile.physical_width_pt / profile.width >= 7
    assert max(p["x"] + p["width"] / 2 for p in plotted) <= profile.width


def test_smooth_trace_keeps_exact_endpoints_and_transition_membership():
    from hop_design.export.construction.survey.traces import trace_commands

    axes = [
        {"definition": {"key": "a"}, "x": 0.0, "y": {1: 10.0}, "band": 0},
        {"definition": {"key": "b"}, "x": 100.0, "y": {2: 90.0}, "band": 0},
    ]
    path = trace_commands(axes, {"values": {"a": 1, "b": 2}})
    assert path.startswith("M0.0000 10.0000") and path.endswith("100.0000 90.0000")
    assert "C" in path and "L" not in path
    assert path == trace_commands(
        axes, {"values": {"a": 1, "b": 2}, "materialized_realization_id": "another"}
    )


def test_literal_features_preserve_recorded_order_and_encoding():
    from hop_design.export.construction.survey.comparison_vector import render_comparison_vector

    fields = [
        {
            "key": f"shape.dimension{i}",
            "label": f"Dimension {i}",
            "unit": "bp",
            "value": i,
            "encoded": i,
        }
        for i in range(5)
    ]
    fields += [
        {
            "key": "sequences.basal_pairs",
            "label": "Basal contacts",
            "unit": "",
            "value": [["A", "T", "watson_crick"]] * 18,
            "encoding": "contacts",
            "encoded": [2] * 18,
        },
        {
            "key": "sequences.foldback_pairs",
            "label": "Foldback contacts",
            "unit": "",
            "value": [["C", "G", "watson_crick"]] * 6,
            "encoding": "contacts",
            "encoded": [4] * 6,
        },
        {
            "key": "sequences.loop",
            "label": "Loop",
            "unit": "",
            "value": ["C", "G", "G", "G"],
            "encoded": ["C", "G", "G", "G"],
        },
    ]
    fields += [
        {
            "key": f"interfaces.{side}_word",
            "label": side + " sticky end",
            "unit": "",
            "value": "CGAG",
            "encoded": "CGAG",
        }
        for side in ["left", "right"]
    ]
    packet = display_packet({"identity": "example", "vector": fields})
    before = json.dumps(packet, sort_keys=True)
    root = ET.fromstring(render_comparison_vector(packet, width_pt=246))
    assert root.get("data-comparison-display") == "numeric-row"
    assert float(root.get("viewBox").split()[2]) <= 504
    assert [g.get("data-feature") for g in root.iter() if g.get("data-feature")] == [
        f["key"] for f in fields
    ]
    assert [json.loads(g.get("data-encoded")) for g in root.iter() if g.get("data-encoded")] == [
        f["encoded"] for f in fields
    ]
    assert not any((e.text or "").startswith("x =") for e in root.iter() if e.tag.endswith("text"))
    assert json.dumps(packet, sort_keys=True) == before


def test_column_categories_stay_horizontal_with_ink_bounded_headings():
    from hop_design.export.construction.presentation.figure_profile import COLUMN_DETAIL_FIGURE
    from hop_design.export.construction.survey.layout import node_geometry, plot_layout

    axis = {
        "key": "foldback_method",
        "label": "Foldback nickase",
        "symbol": "E",
        "kind": "categorical",
        "representation": "recognition",
        "unit": "",
        "neighborhood": "foldback",
        "nodes": [{"value": "Nt.Bpu10I", "label": "Nt.Bpu10I", "supported_preparations": 1}],
    }
    geometry = node_geometry(axis, axis["nodes"][0], profile=COLUMN_DETAIL_FIGURE)
    assert not geometry.get("rotation")
    assert geometry["height"] < geometry["width"]
    frame = plot_layout({"axes": [axis]}, profile=COLUMN_DETAIL_FIGURE).frame
    assert frame.heading_y > frame.bottom


def test_column_contact_blocks_share_a_reading_row():
    from hop_design.export.construction.survey.comparison_vector import render_comparison_vector

    def contacts(key, n):
        return {
            "key": "sequences." + key,
            "label": key,
            "encoding": "contacts",
            "encoded": [0] * n,
            "value": [["A", "T", "watson_crick"]] * n,
        }

    root = ET.fromstring(
        render_comparison_vector(
            display_packet(
                {
                    "identity": "example",
                    "vector": [contacts("basal_pairs", 18), contacts("foldback_pairs", 6)],
                }
            ),
            width_pt=246,
        )
    )
    blocks = [e for e in root.iter() if e.get("data-feature")]
    labels = [next(e for e in b if e.tag.endswith("text")) for b in blocks]
    assert labels[0].get("y") == labels[1].get("y")
    assert float(labels[0].get("x")) < float(labels[1].get("x"))


def test_column_layout_reports_insufficient_width_instead_of_tiny_labels():
    import pytest

    from hop_design.export.construction.presentation.figure_profile import COLUMN_DETAIL_FIGURE
    from hop_design.export.construction.survey.layout import plot_layout

    axes = [
        {
            "key": str(i),
            "label": "Enzyme",
            "symbol": "E",
            "kind": "categorical",
            "representation": "recognition",
            "unit": "",
            "nodes": [
                {
                    "value": "VeryLongEnzymeName",
                    "label": "VeryLongEnzymeName",
                    "supported_preparations": 1,
                }
            ],
        }
        for i in range(12)
    ]
    with pytest.raises(ValueError, match=r"at least.*points"):
        plot_layout({"axes": axes}, profile=COLUMN_DETAIL_FIGURE)


def test_selected_trace_context_is_metadata_only():
    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
    from hop_design.export.construction.survey.plot import render_survey_plot
    from tests.unit.test_survey_plot import choices

    root = ET.fromstring(render_survey_plot(choices(), profile=INSPECTOR_FIGURE))
    context = next(e for e in root.iter() if e.get("data-plot-context"))
    assert not any(e.tag.endswith("text") for e in context.iter())
    assert any(e.get("data-complete-plot-context") for e in context.iter())
    assert root.get("viewBox") == root.get("data-landscape-frame")


def test_inspector_trace_uses_shared_compact_language_at_fitted_width():
    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
    from hop_design.export.construction.survey.plot import render_survey_plot
    from tests.unit.test_survey_plot import choices

    root = ET.fromstring(render_survey_plot(choices(), profile=INSPECTOR_FIGURE))
    assert float(root.get("font-size")) * 672 / float(root.get("viewBox").split()[2]) >= 12
    assert any(e.get("data-heading-angle") == "-45" for e in root.iter())
    assert not any(
        e.get("transform", "").startswith("rotate")
        for e in root.iter()
        if e.get("data-node-label") == "true" and e.tag.endswith("text")
    )


def test_literal_x_is_one_horizontal_row_with_lossless_values():
    from hop_design.export.construction.survey.comparison_vector import render_comparison_vector

    packet = {
        "identity": "example",
        "vector": [
            {"key": "shape.loop_nt", "label": "Loop size", "unit": "nt", "value": 4, "encoded": 4},
            {
                "key": "sequences.basal_pairs",
                "label": "Basal contacts",
                "encoding": "contacts",
                "value": [["A", "T", "watson_crick"]] * 18,
                "encoded": [2] * 18,
            },
            {
                "key": "interfaces.right_word",
                "label": "Right sticky end",
                "value": "CAAG",
                "encoded": "CAAG",
            },
        ],
    }
    packet = display_packet(packet)
    root = ET.fromstring(render_comparison_vector(packet))
    assert root.get("data-comparison-display") == "numeric-row"
    assert any(e.text == "X =" for e in root.iter() if e.tag.endswith("text"))
    assert len([e for e in root.iter() if e.get("data-vector-bracket")]) == 2
    fields = [e for e in root.iter() if e.get("data-feature")]
    assert {e.get("data-feature-row") for e in fields} == {"0"}
    assert [json.loads(e.get("data-encoded")) for e in fields] == [
        f["encoded"] for f in packet["vector"]
    ]
    assert float(root.get("viewBox").split()[2]) <= 504
