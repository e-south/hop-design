"""Facet availability ignores only its own predicate and counts each row once."""

import copy

import pytest

from hop_design.design.construction.editions.projection import project_choices
from hop_design.design.construction.surveys.selection import load_query
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery

SNAPSHOT = "sha256:" + "a" * 64


def index():
    return {
        "snapshot_digest": SNAPSHOT,
        "coverage": {},
        "axes": [
            {"key": key, "nodes": [{"value": value, "state": state} for value, state in values]}
            for key, values in (
                (
                    "loop_word",
                    [
                        ("AAAA", "supported"),
                        ("AACA", "supported"),
                        ("CCCC", "excluded_in_scope"),
                        ("TTTT", "unresolved"),
                    ],
                ),
                ("left_gap", [(0, "supported"), (6, "supported")]),
            )
        ],
        "paths": [
            {
                "materialized_realization_id": name,
                "values": {"loop_word": loop, "left_gap": gap},
                "molecular_identity": {"hairpin": molecule},
            }
            for name, loop, gap, molecule in (
                ("a", "AAAA", 0, "one"),
                ("b", "AACA", 0, "two"),
                ("c", "AACA", 6, "two"),
            )
        ],
    }


def test_counts_keep_conditional_global_and_absent_support_distinct():
    source = index()
    before = copy.deepcopy(source)
    query = load_query(
        {
            "parameters": [
                {"key": "loop_word", "values": ["AAAA"]},
                {"key": "left_gap", "values": [0]},
            ]
        }
    )
    result = project_choices(source, query)
    assert result["matching_preparations"] == 1
    assert result["matching_products"] == {"hairpin": 1}
    assert [p["matches"] for p in result["paths"]] == [True, False, False]
    loop, gap = [axis["nodes"] for axis in result["axes"]]
    assert [
        (n["supported_preparations"], n["conditional_preparations"], n["state"]) for n in loop
    ] == [
        (1, 1, "supported"),
        (2, 1, "supported"),
        (0, 0, "excluded_in_scope"),
        (0, 0, "unresolved"),
    ]
    assert [(n["conditional_preparations"], n["state"]) for n in gap] == [
        (1, "supported"),
        (0, "supported_elsewhere"),
    ]
    assert source == before


@pytest.mark.parametrize("members", [[], ["c"]])
def test_membership_applies_to_every_conditional_count(members):
    result = project_choices(
        index(),
        load_query(
            {
                "membership": {"snapshot_digest": SNAPSHOT, "preparations": members},
                "parameters": [{"key": "left_gap", "values": [0]}],
            }
        ),
    )
    assert result["matching_preparations"] == 0
    assert [n["conditional_preparations"] for n in result["axes"][0]["nodes"]] == [0, 0, 0, 0]
    assert [n["conditional_preparations"] for n in result["axes"][1]["nodes"]] == [0, len(members)]


def test_node_domain_size_does_not_multiply_path_scans():
    class CountedValues(dict):
        reads = 0

        def get(self, key, default=None):
            type(self).reads += 1
            return super().get(key, default)

    source = index()
    source["axes"] = [
        {"key": "left_gap", "nodes": [{"value": n, "state": "unresolved"} for n in range(256)]}
    ]
    for path in source["paths"]:
        path["values"] = CountedValues(path["values"])
    result = project_choices(source, InterfaceSurveyQuery())
    assert sum(n["supported_preparations"] for n in result["axes"][0]["nodes"]) == 3
    # One row scan may read the coordinate for global and conditional counts;
    # adding unresolved values must not cause another scan of all preparations.
    assert CountedValues.reads <= 2 * len(source["paths"])
