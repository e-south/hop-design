"""Strict context names and measurement intersections without molecular replay."""

import json
from copy import deepcopy

import pytest

from hop_design import construction
from hop_design.design.construction.intents.query import resolve_query
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.serialization import canonical_json_bytes
from tests.unit.test_construction_intent import STEM


@pytest.fixture
def permissions():
    return json.loads(
        construction.resolve_design_request(
            {
                "stem_arm": STEM,
                "product": "released_insert",
            }
        ).json_bytes
    )["permissions"]


def test_ambiguous_names_need_ids_in_both_intent_and_refinement(permissions):
    enzymes = permissions["enzyme_catalog"]["enzymes"]
    original = next(e for e in enzymes if e["canonical_name"] == "BsaI-HFv2")
    duplicate = deepcopy(original)
    duplicate["enzyme_id"] = "example:enzyme/alternative-bsai@1"
    enzymes.append(duplicate)
    policy = permissions["release"]["enzymes"]
    policy["allowed_enzyme_ids"].append(duplicate["enzyme_id"])
    for restriction in policy["role_restrictions"]:
        if restriction["role"] == "end_generation":
            restriction["allowed_enzyme_ids"].append(duplicate["enzyme_id"])
    query = InterfaceSurveyQuery.model_validate_json(
        canonical_json_bytes(
            {
                "parameters": [{"key": "release_method", "values": ["BsaI-HFv2"]}],
            }
        )
    )
    with pytest.raises(ValueError, match=r"Ambiguous release.*exact catalog ID"):
        resolve_query(query, permissions)
    with pytest.raises(ValueError, match=r"Ambiguous release.*exact catalog ID"):
        construction.resolve_design_request(
            {
                "stem_arm": STEM,
                "product": "released_insert",
                "context": permissions,
                "methods": {"release": ["BsaI-HFv2"]},
            }
        )
    identified = query.model_dump(mode="json", by_alias=True)
    identified["parameters"][0]["values"] = [original["enzyme_id"]]
    explicit = InterfaceSurveyQuery.model_validate_json(canonical_json_bytes(identified))
    assert resolve_query(explicit, permissions) == explicit


@pytest.mark.parametrize(
    "left,right",
    [
        ({"values": [4, 6]}, {"values": [5, 7]}),
        ({"minimum": 4, "maximum": 6}, {"minimum": 7, "maximum": 9}),
    ],
)
def test_nonoverlapping_equivalent_domains_reject(permissions, left, right):
    query = InterfaceSurveyQuery.model_validate_json(
        canonical_json_bytes(
            {
                "parameters": [
                    {"key": "foldback_arm_bp", **left},
                    {"key": "loop_side_paired_bp", **right},
                ]
            }
        )
    )
    with pytest.raises(ValueError, match=r"Equivalent hairpin.*conflict"):
        resolve_query(query, permissions)


def test_name_and_id_duplicates_do_not_gain_extra_sampling_weight(permissions):
    query = InterfaceSurveyQuery.model_validate_json(
        canonical_json_bytes(
            {
                "parameters": [
                    {
                        "key": "release_method",
                        "values": ["BsaI-HFv2", "example:enzyme/bsai-hfv2@1"],
                    },
                ]
            }
        )
    )
    with pytest.raises(ValueError, match="must not repeat"):
        resolve_query(query, permissions)
