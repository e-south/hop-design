"""Current views teach one vocabulary without rewriting captured molecular facts."""

import copy
import json
from xml.etree import ElementTree as ET

import pytest

from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.export.construction.survey.traces import TraceProjection
from hop_design.models.construction.variants.parameters import parameter_definition
from tests.unit.test_survey_plot import choices


def historical_choices():
    answer = choices()
    for axis in answer["axes"]:
        if axis["key"] == "left_gap":
            axis["label"] = "Left end-to-stem gap"
        elif axis["key"] == "foldback_arm_bp":
            axis["label"] = "Foldback arm"
    return answer


def test_static_and_interactive_traces_share_current_labels_without_changing_source_values():
    answer = historical_choices()
    before = copy.deepcopy(answer)
    tree = ET.fromstring(render_survey_plot(answer))
    axis = tree.find(".//*[@data-axis-title='left_gap']")
    assert " ".join(e.text for e in axis if e.tag.endswith("}text")) == "Left gap bp"
    trace = TraceProjection(answer).trace("exact-one")
    for value in trace["values"]:
        assert value["label"] == parameter_definition(value["key"]).label
        assert value["value"] == answer["paths"][0]["values"][value["key"]]
    receipt = json.loads(tree.find(".//*[@data-parameter-labels='true']").text)
    assert {r["key"] for r in receipt["renamed"]} == {"left_gap", "foldback_arm_bp"}
    assert answer == before


def test_browser_label_projection_shares_paths_and_preserves_every_other_axis_field():
    from hop_design.api import _InspectionProjection

    answer = historical_choices()
    before = copy.deepcopy(answer)
    display = _InspectionProjection.display(answer)
    assert display["paths"] is answer["paths"]
    assert display["query"] is answer["query"]
    for old, new in zip(answer["axes"], display["axes"], strict=True):
        assert new["label"] == parameter_definition(old["key"]).label
        assert {k: v for k, v in old.items() if k != "label"} == {
            k: v for k, v in new.items() if k != "label"
        }
    assert answer == before


@pytest.mark.parametrize(
    "change", [{"unit": "nt"}, {"stage": "source_duplex"}, {"key": "future_gap"}]
)
def test_incompatible_or_unknown_definitions_keep_their_captured_label_with_a_notice(change):
    from hop_design.export.construction.presentation.parameter_labels import parameter_labels

    source = next(a for a in historical_choices()["axes"] if a["key"] == "left_gap")
    source.update(change)
    projected, receipt = parameter_labels([source])
    assert projected == [source]
    assert receipt["renamed"] == []
    assert receipt["retained"][0]["key"] == source["key"]
    assert receipt["retained"][0]["reason"]
