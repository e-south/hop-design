"""More work cannot satisfy a filter outside the saved molecular permissions."""

import json

import pytest

from hop_design.models.construction.surveys.query import InterfaceSurveyQuery


@pytest.mark.parametrize("values,expected", [([4], True), ([99], False), ([4, 99], True)])
def test_remaining_search_requires_overlap_with_declared_values(values, expected):
    from hop_design.design.construction.intents.query import parameters_permitted

    query = InterfaceSurveyQuery.model_validate_json(
        json.dumps({"parameters": [{"key": "loop_nt", "values": values}]})
    )
    axes = [{"key": "loop_nt", "domain": {"values": [3, 4, 6]}}]
    assert parameters_permitted(query, axes) is expected
    assert parameters_permitted(query, [])  # Absent coverage is not an exclusion proof.
