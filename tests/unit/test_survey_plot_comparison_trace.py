"""
--------------------------------------------------------------------------------
HOP Design
hop-design/tests/unit/test_survey_plot_comparison_trace.py

Keep comparison traces aligned with the saved X schema and exact membership.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from copy import deepcopy

import pytest

from hop_design.export.construction.survey.comparison_trace import comparison_trace_choices


def packet():
    return {
        "presentation": {"display_order": ["sequences.basal_pairs", "shape.loop_nt"]},
        "contacts": [["A", "T", "watson_crick"], ["G", "T", "gt_wobble"]],
        "columns": [
            {
                "key": "shape.loop_nt",
                "label": "Loop length",
                "unit": "nt",
                "active": True,
                "dictionary": [3, 4],
                "indices": [0, 1],
                "parameters": ["loop_nt"],
            },
            {
                "key": "sequences.basal_pairs",
                "label": "Basal pattern",
                "unit": "",
                "active": True,
                "dictionary": [[0, 1], [1, 0]],
                "indices": [0, 1],
                "encoding": "contacts",
                "parameters": ["open_side_paired_positions"],
            },
        ],
    }


def choices():
    return {
        "axes": [],
        "request_digest": "request",
        "snapshot_digest": "snapshot",
        "query_digest": "query",
        "query": {"parameters": []},
        "paths": [
            {"materialized_realization_id": identity, "matches": True, "values": {"loop_nt": value}}
            for identity, value in [("a", 3), ("b", 4)]
        ],
    }


def test_trace_uses_saved_x_order_names_and_exact_pattern_categories():
    original, comparison = choices(), packet()
    before = deepcopy((original, comparison))
    result = comparison_trace_choices(original, comparison)
    assert [a["key"] for a in result["axes"]] == comparison["presentation"]["display_order"]
    assert [a["label"] for a in result["axes"]] == ["Basal pattern", "Loop length"]
    assert result["axes"][0]["kind"] == "categorical"
    assert result["axes"][0]["nodes"][0]["display_lines"] == ["AG", "TT"]
    assert all(a["read_only"] for a in result["axes"])
    assert [p["values"]["sequences.basal_pairs"] for p in result["paths"]] == [0, 1]
    assert [p["values"]["shape.loop_nt"] for p in result["paths"]] == [3, 4]
    assert result["paths"][0]["values"]["loop_nt"] == 3
    assert (original, comparison) == before


def test_bad_comparison_membership_or_field_order_fails_before_drawing():
    bad = packet()
    bad["columns"][0]["indices"] = [0]
    with pytest.raises(ValueError, match="member"):
        comparison_trace_choices(choices(), bad)


def test_position_only_map_retains_its_existing_parameter_plot():
    original = choices()
    assert comparison_trace_choices(original, {"columns": []}) is original


def test_native_trace_and_selected_overlay_share_values_and_molecular_links():
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
    from hop_design.export.construction.survey.figure_layout import plot_geometry
    from hop_design.export.construction.survey.plot import render_survey_plot
    from hop_design.export.construction.survey.traces import TraceProjection

    result = comparison_trace_choices(choices(), packet())
    fields = tuple(a["key"] for a in result["axes"])
    root = ET.fromstring(render_survey_plot(result, profile=INSPECTOR_FIGURE, display_axes=fields))
    projection = TraceProjection(result, profile=INSPECTOR_FIGURE, display_axes=fields)
    assert plot_geometry(root) == projection.figure_geometry
    assert projection.trace("a")["values"][0]["node_label"]["lines"] == ["AG", "TT"]
    bad = packet()
    bad["presentation"]["display_order"] = ["shape.loop_nt", "shape.loop_nt"]
    with pytest.raises(ValueError, match="order"):
        comparison_trace_choices(choices(), bad)
