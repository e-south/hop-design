"""
--------------------------------------------------------------------------------
HOP Design
tests/unit/test_design_query_admission.py

Require query mappings before dispatch while preserving optional and refined inputs.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json

import pytest

from hop_design.design.construction.intents.refinement import load_design_query
from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery


@pytest.mark.parametrize("source", [False, 0, [], True, 1, [1], (), b"", object()])
def test_non_mapping_inline_query_raises_value_error(source):
    with pytest.raises(ValueError, match="mapping"):
        load_design_query(source)


@pytest.mark.parametrize("source", [None, {}])
def test_omitted_and_explicit_empty_mapping_remain_unrestricted(source):
    assert load_design_query(source) == InterfaceSurveyQuery()


@pytest.mark.parametrize("refined", [False, True])
def test_native_and_refined_query_mappings_keep_file_parity(tmp_path, refined):
    source = {"parameters": [{"key": "left_gap", "values": [6]}]}
    if refined:
        source.update(
            schema="hop.design-refinement/v1",
            reference={
                "request_digest": "sha256:" + "a" * 64,
                "snapshot_digest": "sha256:" + "b" * 64,
                "materialized_realization_id": "fixture-preparation",
            },
            surroundings={"stage": "endpoint", "except_neighborhood": "loop"},
        )
    path = tmp_path / "query.json"
    path.write_text(json.dumps(source))
    admitted = load_design_query(source)
    assert isinstance(admitted, DesignRefinementQuery if refined else InterfaceSurveyQuery)
    assert load_design_query(path) == admitted
    assert source["parameters"] == [{"key": "left_gap", "values": [6]}]
