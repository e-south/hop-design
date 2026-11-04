"""A complete-path plot preserves dense permission and publication-scale meaning."""

import copy
import json
from xml.etree import ElementTree as ET

import pytest

from hop_design.design.construction.surveys.parameter_key import AXIS_ORDER
from hop_design.export.construction.survey.figure import compose_figure
from hop_design.export.construction.survey.layout import FONT
from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.export.construction.survey.presentation import present_choices
from hop_design.models.construction.surveys.targets import FOUR_BASE_WORDS
from hop_design.models.construction.variants.parameters import parameter_definition


def choices():
    axes = []
    for key in AXIS_ORDER:
        definition = parameter_definition(key).model_dump(mode="json")
        values = (
            FOUR_BASE_WORDS
            if key == "left_end_word"
            else (0, 1, 6)
            if definition["kind"] == "numeric"
            else ("AAAA",)
        )
        nodes = [
            {
                "value": v,
                "label": str(v),
                "state": "unresolved",
                "supported_preparations": 0,
                "conditional_preparations": 0,
            }
            for v in values
        ]
        axes.append(
            {**definition, "nodes": nodes, "domain": {"basis": "declared", "values": values}}
        )
    values = {a["key"]: a["nodes"][0]["value"] for a in axes}
    values["left_end_word"] = "TGCA"
    for axis in axes:
        for node in axis["nodes"]:
            if node["value"] == values[axis["key"]]:
                node.update(state="supported", supported_preparations=1, conditional_preparations=1)
    axes[0]["nodes"][0]["state"] = "excluded_in_scope"
    axes[0]["nodes"][1].update(state="supported_elsewhere", supported_preparations=1)
    return {
        "axes": axes,
        "paths": [
            {
                "address": {"target": 1, "step": 0},
                "materialized_realization_id": "exact-one",
                "values": values,
                "matches": True,
            }
        ],
        "query": {"parameters": []},
        "snapshot_digest": "snapshot",
        "request_digest": "request",
        "query_digest": "query",
    }


def test_compact_plate_connects_located_features_without_expanding_into_context_text():
    records = choices()
    plot = render_survey_plot(records)
    key = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1008 230">
      <g data-parameter-anchor="loop_nt" data-anchor-box="[900,80,40,60]"/>
      <g data-parameter-anchor="left_gap" data-anchor-box="[100,80,60,60]"/>
    </svg>"""
    figure = ET.fromstring(compose_figure(key, plot, records, selected_identity="exact-one"))
    links = {e.get("data-parameter-link") for e in figure.iter() if e.get("data-parameter-link")}
    assert links == {"loop_nt", "left_gap"}
    assert not any(e.get("data-plot-context") for e in figure.iter())
    plot_axes = [e.get("data-axis") for e in figure.iter() if e.get("data-axis")]
    assert plot_axes.index("left_gap") < plot_axes.index("loop_nt")
    # No additional paths or eligibility values are introduced by correspondence.
    assert [e.get("data-members") for e in figure.iter() if e.get("data-members")] == [
        e.get("data-members") for e in ET.fromstring(plot).iter() if e.get("data-members")
    ]


def test_design_view_prints_plain_labels_and_methods_and_keeps_fixed_context_off_axes():
    records = choices()
    method = next(a for a in records["axes"] if a["key"] == "release_method")
    method["nodes"][0]["label"] = "BsaI-HFv2"
    drawing = ET.fromstring(render_survey_plot(records, selected_identity="exact-one"))
    axes = {e.get("data-axis") for e in drawing.iter() if e.get("data-axis")}
    text = " ".join(e.text or "" for e in drawing.iter() if e.tag.endswith("}text"))
    assert {"loop_nt", "foldback_arm_bp", "left_gap", "right_gap"} <= axes
    assert "self_paired_arm_bp" not in axes
    assert "release_method" not in axes
    assert "BsaI-HFv2" in text
    assert "Loop size" in text and "Left gap" in text
    assert "eR1" not in text
    assert float(drawing.get("font-size")) * 504 / float(drawing.get("viewBox").split()[2]) >= 9


def test_plot_context_can_be_disclosed_without_removing_coordinates():
    drawing = ET.fromstring(render_survey_plot(choices()))
    context = drawing.find(".//*[@data-plot-context='true']")
    assert context is not None
    assert not any(e.get("data-axis") or e.get("data-members") for e in context.iter())
    frame = list(map(float, drawing.attrib["data-landscape-frame"].split()))
    assert frame[3] < float(drawing.attrib["viewBox"].split()[3])
    assert all(float(e.attrib["y"]) >= frame[3] for e in context if e.tag.endswith("}text"))


def test_all_nodes_and_whole_paths_survive_publication_projection():
    drawing = ET.fromstring(render_survey_plot(choices(), selected_identity="exact-one"))
    assert (
        float(drawing.attrib["font-size"]) * 504 / float(drawing.attrib["viewBox"].split()[2]) >= 7
    )
    axes = [e for e in drawing.iter() if e.get("data-axis")]
    assert [e.attrib["data-axis"] for e in axes] == [
        a["key"] for a in present_choices(choices())["axes"]
    ]
    assert all(parameter_definition(key).symbol for key in AXIS_ORDER)
    left = next(e for e in axes if e.attrib["data-axis"] == "left_end_word")
    nodes = [e for e in left.iter() if e.get("data-node-value")]
    assert len(nodes) == 256
    assert {e.attrib["data-support-state"] for e in nodes} == {
        "supported",
        "supported_elsewhere",
        "unresolved",
        "excluded_in_scope",
    }
    selected = next(e for e in nodes if e.attrib["data-node-value"] == '"TGCA"')
    assert "TGCA" in "".join(e.text or "" for e in selected if e.tag.endswith("text"))
    traces = [e for e in drawing.iter() if e.get("data-members")]
    assert len(traces) == 1 and "exact-one" in traces[0].attrib["data-members"]
    assert "labels" in "".join(drawing.itertext()).lower()
    assert any(e.get("data-brush-axis") == "left_gap" for e in drawing.iter())


def test_dense_ticks_keep_exclusion_distinct_from_unresolved():
    drawing = ET.fromstring(render_survey_plot(choices()))
    marks = {
        e.attrib["data-support-state"]: e.attrib for e in drawing.iter() if e.get("data-node-mark")
    }
    assert marks["unresolved"]["stroke-dasharray"] != marks["excluded_in_scope"]["stroke-dasharray"]
    assert marks["unresolved"]["stroke"] != marks["excluded_in_scope"]["stroke"]


def test_dense_axis_ticks_cannot_paint_over_readable_value_cells():
    drawing = ET.fromstring(render_survey_plot(choices()))
    for axis in (e for e in drawing.iter() if e.get("data-axis")):
        rectangles = []
        for element in axis.iter():
            if element.get("data-node-mark"):
                y = float(element.get("y1"))
                assert not any(top < y < bottom for top, bottom in rectangles)
            if element.tag.endswith("}rect") and element.get("data-node-label"):
                top = float(element.get("y"))
                rectangles.append((top, top + float(element.get("height"))))


def test_filtering_preserves_positions_and_overlapping_preparations_remain_distinct():
    records = choices()
    first = records["paths"][0]
    records["paths"].extend(
        [
            {**first, "materialized_realization_id": "exact-two"},
            {**first, "address": {"target": 2, "step": 0}},
        ]
    )
    before = ET.fromstring(render_survey_plot(records))
    filtered = copy.deepcopy(records)
    filtered["query"]["parameters"] = [{"key": "left_end_word", "values": ["AAAA"]}]
    for path in filtered["paths"]:
        path["matches"] = False
    after = ET.fromstring(render_survey_plot(filtered))

    def positions(svg):
        return {
            (e.get("data-parameter"), e.get("data-node-value")): e.get("data-y")
            for e in svg.iter()
            if e.get("data-node-value")
        }

    assert positions(before) == positions(after)
    paths = [e for e in after.iter() if e.get("data-members")]
    assert len(paths) == 1
    assert json.loads(paths[0].attrib["data-members"]) == ["exact-one", "exact-two"]
    pin = next(
        e
        for e in after.iter()
        if e.get("data-parameter") == "left_end_word" and e.get("data-node-value") == '"AAAA"'
    )
    assert pin.get("data-pinned") == "true"
    assert any(e.get("data-query-pin") for e in pin)
    del filtered["paths"][0]["values"]["left_gap"]
    with pytest.raises(ValueError, match="missing a declared coordinate"):
        render_survey_plot(filtered)


def test_unfiltered_permission_context_is_not_reported_as_an_active_query():
    records = choices()
    for key in ("basal_release_product_end", "basal_release_recognition_material"):
        records["axes"].append(
            {
                **parameter_definition(key).model_dump(mode="json"),
                "domain": {"basis": "declared"},
                "nodes": [],
            }
        )
    drawing = ET.fromstring(render_survey_plot(records))
    assert json.loads(drawing.attrib["data-context-parameters"]) == []
    assert "additional query predicates" not in "".join(drawing.itertext())
    records["query"]["parameters"] = [
        {"key": "basal_release_recognition_material", "values": ["endpoint_material"]}
    ]
    drawing = ET.fromstring(render_survey_plot(records))
    assert json.loads(drawing.attrib["data-context-parameters"]) == [
        "basal_release_recognition_material"
    ]
    assert "1 additional query predicates" in "".join(drawing.itertext())


def test_position_specific_filter_does_not_invent_an_additional_coarse_coordinate():
    records = choices()
    records["axes"].append(
        {
            **parameter_definition("basal_source_base_999").model_dump(mode="json"),
            "domain": {"basis": "observed_only"},
            "nodes": [],
        }
    )
    records["query"]["parameters"] = [{"key": "basal_source_base_999", "values": ["A"]}]
    records["paths"][0]["matches"] = False
    drawing = ET.fromstring(render_survey_plot(records))
    assert [e.get("data-axis") for e in drawing.iter() if e.get("data-axis")] == [
        a["key"] for a in present_choices(choices())["axes"]
    ]
    assert json.loads(drawing.attrib["data-context-parameters"]) == ["basal_source_base_999"]
    assert len([e for e in drawing.iter() if e.get("data-members")]) == 1


def test_long_words_do_not_collide_with_headers_or_leave_the_data_band():
    records = choices()
    axis = next(a for a in records["axes"] if a["key"] == "loop_word")
    word = "ACGT" * 16
    axis["nodes"][0].update(value=word, label=word)
    axis["domain"] = {"basis": "observed_only"}
    records["paths"][0]["values"]["loop_word"] = word
    records["query"]["parameters"] = [{"key": "loop_word", "values": [word]}]
    drawing = ET.fromstring(render_survey_plot(records, selected_identity="exact-one"))
    frame = json.loads(drawing.get("data-axis-frame"))
    for axis_group in (e for e in drawing.iter() if e.get("data-axis")):
        offset = int(axis_group.get("data-band")) * frame["height"]
        for node in (e for e in axis_group if e.get("data-node-value")):
            for rect in (e for e in node if e.tag.endswith("}rect")):
                y = float(rect.attrib["y"])
                assert y >= offset + frame["top"] - FONT
                assert y + float(rect.attrib["height"]) <= offset + frame["bottom"] + FONT
    node = next(e for e in drawing.iter() if e.get("data-node-value") == json.dumps(word))
    assert "64 nt" in "".join(e.text or "" for e in node if e.tag.endswith("}text"))
    assert word in "".join(node.itertext())


def test_numeric_query_range_is_distinct_from_support_and_clears_explicitly():
    records = choices()
    records["query"]["parameters"] = [{"key": "left_gap", "minimum": 0, "maximum": 1}]
    svg = ET.fromstring(render_survey_plot(records))
    nodes = [
        e for e in svg.iter() if e.get("data-parameter") == "left_gap" and e.get("data-node-value")
    ]
    assert {
        json.loads(e.attrib["data-node-value"]) for e in nodes if e.get("data-pinned") == "true"
    } == {0, 1}
    # The value 1 remains unresolved even though the query permits it.
    one = next(e for e in nodes if e.get("data-node-value") == "1")
    assert one.attrib["data-support-state"] == "unresolved"
    records["query"]["parameters"] = []
    cleared = ET.fromstring(render_survey_plot(records))
    assert not any(e.get("data-pinned") == "true" for e in cleared.iter())


def test_long_sequence_details_stay_in_the_domain_export_not_the_compact_plate():
    from hop_design.export.construction.survey.figure import compose_figure, domain_csv

    records = choices()
    axis = next(a for a in records["axes"] if a["key"] == "loop_word")
    word = "ACGT" * 100
    axis["nodes"][0].update(value=word, label=word)
    records["paths"][0]["values"]["loop_word"] = word
    key = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 10" />'
    drawing = ET.fromstring(compose_figure(key, render_survey_plot(records), records))
    assert not any(e.get("data-domain-key") for e in drawing.iter())
    assert word in "".join(ET.fromstring(render_survey_plot(records)).itertext())
    assert word.encode() in domain_csv(records)


def test_axes_retain_the_teaching_regions_and_visible_group_labels():
    drawing = ET.fromstring(render_survey_plot(choices()))
    axes = [e for e in drawing.iter() if e.get("data-axis")]
    assert all(e.get("data-region") in {"assembly", "closing", "interfaces"} for e in axes)
    regions = [e for e in drawing.iter() if e.get("data-axis-region")]
    assert {e.get("data-axis-region") for e in regions} == {"assembly", "closing", "interfaces"}
    assert all(e.get("fill") for e in regions)


def test_categorical_supported_words_remain_readable_among_unresolved_permissions():
    records = choices()
    axis = next(a for a in records["axes"] if a["key"] == "left_end_word")
    for n in axis["nodes"]:
        if n["value"] in {"AAAA", "AAAC", "AAAG"}:
            n.update(state="supported", supported_preparations=1, conditional_preparations=1)
    svg = ET.fromstring(render_survey_plot(records))
    nodes = [
        e
        for e in svg.iter()
        if e.get("data-parameter") == "left_end_word" and e.get("data-node-value")
    ]
    assert len(nodes) == 256
    visible = {
        json.loads(e.get("data-node-value"))
        for e in nodes
        if any(c.tag.endswith("}text") for c in e)
    }
    assert {"AAAA", "AAAC", "AAAG", "TGCA"} <= visible


def test_single_base_links_mark_their_exact_origin_behind_the_labels():
    from hop_design.export.construction.survey.figure_layout import (
        add_layout_links,
        figure_layout,
        plot_geometry,
        teaching_geometry,
    )

    root = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="white"/><g id="ink"/></svg>'
    )
    key = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 300">'
        '<g data-parameter-anchor="base" data-anchor-box="[100,80,14,20]"/></svg>'
    )
    plot = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 300">'
        '<g data-axis="base" data-band="0"><g data-axis-title="true">'
        '<text x="200" y="30">Source base</text></g></g></svg>'
    )
    add_layout_links(root, figure_layout(teaching_geometry(key), plot_geometry(plot)))
    mark = next(e for e in root.iter() if e.get("data-parameter-origin"))
    assert mark.get("data-parameter-origin") == "base"
    assert float(mark.get("x")) <= 100 and float(mark.get("x")) + float(mark.get("width")) >= 114
    assert list(root)[1].get("data-teaching-fans") == "true"
