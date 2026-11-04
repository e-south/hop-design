"""Sampling has exact preparation identity semantics, independent of row duplication."""

import pytest

from hop_design.design.construction.surveys.selection import load_query, sample_path


def test_sampling_deduplicates_identities_and_ignores_input_order():
    paths = [
        {
            "materialized_realization_id": word,
            "address": {"target": i, "step": 0},
            "values": {"loop_word": word},
        }
        for i, word in enumerate(("AAAC", "AACA", "AAAA"))
    ]
    duplicate = {**paths[0], "address": {"target": 10, "step": 1}}
    query = load_query({"parameters": [{"key": "loop_word", "values": ["AAAC", "AACA"]}]})
    selected = set()
    for seed in range(32):
        original = sample_path(paths, query, seed)
        assert sample_path([duplicate, *reversed(paths), duplicate], query, seed) == original
        selected.add(original["materialized_realization_id"])
    assert selected == {"AAAC", "AACA"}


@pytest.mark.parametrize("seed", [-1, 2**64, False, 1.0, "1"])
def test_sampling_rejects_invalid_seeds_before_choosing(seed):
    with pytest.raises(ValueError, match="seed"):
        sample_path([], load_query(None), seed)


def test_projection_counts_exact_preparations_separately_from_repeated_records():
    from hop_design.design.construction.surveys.choices import _project
    from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
    from hop_design.serialization import canonical_json_bytes
    from tests.unit.test_interface_survey_request import survey_document

    request = InterfaceSurveyRequest.model_validate_json(canonical_json_bytes(survey_document()))
    row = {
        "materialized_realization_id": "same-preparation",
        "address": {"target": 0, "step": 0},
        "values": {"left_end_word": "AGTC"},
        "molecular_identity": {"hairpin": "hairpin", "endpoint": "insert"},
        "overhead": {},
        "methods": [],
        "material_roles": {},
    }
    repeated = {**row, "address": {"target": 0, "step": 1}}
    result = _project(request, [row, repeated], {}, False, load_query(None))
    assert result["matching_preparations"] == 1
    assert result["matching_records"] == 2
    node = next(
        n
        for a in result["axes"]
        if a["key"] == "left_end_word"
        for n in a["nodes"]
        if n["value"] == "AGTC"
    )
    assert node["supported_preparations"] == node["conditional_preparations"] == 1
    assert node["supported_records"] == node["conditional_records"] == 2
    assert len(result["paths"]) == 2  # Both exact addresses remain retrievable.
