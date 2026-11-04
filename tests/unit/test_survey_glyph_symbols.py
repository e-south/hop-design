"""Plot abbreviations must be taught visibly, not only in hover metadata."""

import json
from xml.etree import ElementTree as ET

from hop_design.design.construction.surveys.parameter_key import parameter_key
from hop_design.export.construction.molecular.parameter_key import render_parameter_definition_key
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


def test_primary_glyph_teaches_plain_product_features_at_print_size():
    key = parameter_key(InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document())))
    svg = ET.fromstring(render_parameter_definition_key(key))
    text = " ".join(e.text or "" for e in svg.iter() if e.tag.endswith("}text"))
    for label in (
        "Loop size",
        "Loop-side",
        "Basal paired",
        "Left gap",
        "Right gap",
        "Left end",
        "Right end",
        "5\u2032 tail",
        "3\u2032 tail",
    ):
        assert label in text
    assert "Fmin" not in text and "aObs" not in text
    assert float(svg.get("font-size")) * 504 / float(svg.get("viewBox").split()[2]) >= 9
    assert {e.get("data-region") for e in svg.iter()} >= {"assembly", "closing", "interfaces"}
