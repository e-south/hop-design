"""Known interface exclusions must remain distinct from unexamined values."""

import json

from hop_design.design.construction.surveys.choices import _project
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


def test_excluded_value_is_visible_even_when_other_targets_remain_unexamined():
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    result = _project(
        request, [], {}, False, InterfaceSurveyQuery(), excluded_values={"left_end_word": ["AAAA"]}
    )
    axis = next(a for a in result["axes"] if a["key"] == "left_end_word")
    states = {n["value"]: n["state"] for n in axis["nodes"]}
    assert states["AAAA"] == "excluded_in_scope"
    assert states["AAAC"] == "unresolved"
