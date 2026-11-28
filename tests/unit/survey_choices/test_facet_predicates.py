"""
--------------------------------------------------------------------------------
HOP Design
tests/unit/survey_choices/test_facet_predicates.py

Preserve conditional facet counts while bounding repeated query predicates.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json

import pytest

from hop_design.design.construction.surveys.choices import InterfaceSurveyChoices
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.construction.variants.membership import PreparationQuery
from hop_design.serialization import canonical_json_bytes
from tests.unit.test_interface_survey_request import survey_document

DIGEST = "sha256:" + "a" * 64


@pytest.fixture
def pool():
    paths = [
        {
            "address": {"target": 0, "step": position},
            "materialized_realization_id": identity,
            "molecular_identity": {"hairpin": identity, "endpoint": identity},
            "overhead": {},
            "methods": [],
            "material_roles": [],
            "values": {"left_gap": left, "right_gap": right},
        }
        for position, (identity, left, right) in enumerate((("a", 0, 6), ("b", 6, 0), ("c", 6, 6)))
    ]
    choices = object.__new__(InterfaceSurveyChoices)
    object.__setattr__(
        choices,
        "_request",
        InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document())),
    )
    object.__setattr__(choices, "_digest", DIGEST)
    object.__setattr__(
        choices,
        "_snapshot",
        canonical_json_bytes({"paths": paths, "coverage": {}, "fully_enumerated": False}),
    )
    return choices


def nodes(result, key):
    axis = next(axis for axis in result["axes"] if axis["key"] == key)
    return {node["value"]: node for node in axis["nodes"]}


def test_unfiltered_facets_reuse_each_paths_admitted_match(pool, monkeypatch):
    calls = []
    includes = PreparationQuery.includes_preparation

    def counted(query, identity):
        calls.append(identity)
        return includes(query, identity)

    monkeypatch.setattr(PreparationQuery, "includes_preparation", counted)
    result = pool.query()
    assert result["matching_preparations"] == 3
    assert calls == ["a", "b", "c"]


def test_only_filtered_axis_rechecks_membership_and_ignores_its_own_predicate(pool, monkeypatch):
    calls = []
    includes = PreparationQuery.includes_preparation

    def counted(query, identity):
        calls.append(identity)
        return includes(query, identity)

    monkeypatch.setattr(PreparationQuery, "includes_preparation", counted)
    result = pool.query({"parameters": [{"key": "left_gap", "values": [6]}]})
    assert result["matching_preparations"] == 2
    assert len(calls) == 6
    assert nodes(result, "left_gap")[0]["conditional_preparations"] == 1
    assert nodes(result, "left_gap")[6]["conditional_preparations"] == 2
    assert nodes(result, "right_gap")[0]["conditional_preparations"] == 1
    assert nodes(result, "right_gap")[6]["conditional_preparations"] == 1


@pytest.mark.parametrize("identities,matching", [(["a", "c"], 1), ([], 0)])
def test_membership_remains_active_on_own_axis_and_snapshot_stays_detached(
    pool, identities, matching
):
    snapshot = pool._snapshot
    query = {
        "membership": {"snapshot_digest": DIGEST, "preparations": identities},
        "parameters": [{"key": "left_gap", "values": [6]}],
    }
    result = pool.query(query)
    assert result["matching_preparations"] == matching
    assert nodes(result, "left_gap")[0]["conditional_preparations"] == bool(identities)
    assert nodes(result, "left_gap")[6]["conditional_preparations"] == matching
    assert nodes(result, "right_gap")[0]["conditional_preparations"] == 0
    result["paths"].clear()
    assert pool._snapshot == snapshot
    assert len(pool.query(query)["paths"]) == 3


def test_empty_filtered_answer_keeps_own_axis_alternatives(pool):
    result = pool.query({"parameters": [{"key": "left_gap", "values": [100]}]})
    assert result["matching_preparations"] == 0
    assert nodes(result, "left_gap")[0]["conditional_preparations"] == 1
    assert nodes(result, "left_gap")[6]["conditional_preparations"] == 2
    assert all(n["conditional_preparations"] == 0 for n in nodes(result, "right_gap").values())


def test_each_filtered_axis_retains_the_other_axis_predicate(pool):
    result = pool.query(
        {
            "parameters": [
                {"key": "left_gap", "values": [6]},
                {"key": "right_gap", "values": [6]},
            ]
        }
    )
    assert result["matching_preparations"] == 1
    for key in ("left_gap", "right_gap"):
        assert nodes(result, key)[0]["conditional_preparations"] == 1
        assert nodes(result, key)[6]["conditional_preparations"] == 1


def test_unknown_membership_still_raises(pool):
    with pytest.raises(ValueError, match="Unknown preparation"):
        pool.query({"membership": {"snapshot_digest": DIGEST, "preparations": ["missing"]}})
