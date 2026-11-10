"""Column details keep every scientific coordinate and exact feature record."""

import json
from xml.etree import ElementTree as ET


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
    axes = [
        {
            "key": str(i),
            "label": label,
            "symbol": str(i),
            "kind": "categorical" if kind in {"recognition", "sequence"} else "numeric",
            "representation": kind,
            "unit": "",
            "nodes": [{"value": value, "label": value, "supported_preparations": 1}],
        }
        for i, (label, value, kind) in enumerate(labels)
    ]
    plotted = plot_axes({"axes": axes}, profile=COLUMN_DETAIL_FIGURE)
    assert [p["definition"]["key"] for p in plotted] == [a["key"] for a in axes]
    assert {p["band"] for p in plotted} == {0}
    assert COLUMN_DETAIL_FIGURE.axis_font * 246 / COLUMN_DETAIL_FIGURE.width >= 7
    assert max(p["x"] + p["width"] / 2 for p in plotted) <= COLUMN_DETAIL_FIGURE.width


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


def test_column_features_use_named_types_with_unchanged_order_and_encoding():
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
    packet = {"identity": "example", "vector": fields}
    before = json.dumps(packet, sort_keys=True)
    root = ET.fromstring(render_comparison_vector(packet, width_pt=246))
    assert root.get("data-comparison-display") == "typed-features"
    assert float(root.get("viewBox").split()[2]) == 246
    assert [g.get("data-feature") for g in root.iter() if g.get("data-feature")] == [
        f["key"] for f in fields
    ]
    assert [json.loads(g.get("data-encoded")) for g in root.iter() if g.get("data-encoded")] == [
        f["encoded"] for f in fields
    ]
    assert {g.get("data-feature-group") for g in root.iter() if g.get("data-feature-group")} == {
        "Geometry",
        "Contacts and loop",
        "Assembly ends",
    }
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
    assert frame.heading_y - frame.region_height < 125


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
            {
                "identity": "example",
                "vector": [contacts("basal_pairs", 18), contacts("foldback_pairs", 6)],
            },
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
