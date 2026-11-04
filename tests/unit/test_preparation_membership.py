"""Exact group membership must survive conditioning without inventing combinations."""

import json

import pytest

from hop_design.design.construction.editions.projection import project_choices
from hop_design.design.construction.navigation.molecular_groups import molecular_families
from hop_design.design.construction.surveys.selection import load_query
from hop_design.serialization import canonical_json_bytes
from tests.unit.test_molecular_families import path

DIGEST = "sha256:" + "a" * 64


def index():
    rows = [path("a", "one"), path("b", "two"), path("c", "three")]
    for row, left, right in zip(rows, (0, 0, 6), (6, 0, 0), strict=True):
        row["values"].update(left_gap=left, right_gap=right)
    return {
        "paths": rows,
        "snapshot_digest": DIGEST,
        "coverage": {},
        "query": {"schema": "hop.interface-survey-query/v1", "parameters": []},
        "axes": [
            {"key": key, "nodes": [{"value": v, "state": "supported"} for v in (0, 6)]}
            for key in ("left_gap", "right_gap")
        ],
    }


def restricted(*identities, parameters=()):
    return {
        "parameters": list(parameters),
        "membership": {"snapshot_digest": DIGEST, "preparations": list(identities)},
    }


def test_exact_roster_excludes_the_unintended_cross_combination_and_conditions_nodes():
    query = load_query(restricted("a", "c"))
    result = project_choices(index(), query)
    assert [p["materialized_realization_id"] for p in result["paths"] if p["matches"]] == ["a", "c"]
    assert result["matching_preparations"] == 2
    assert result["matching_products"] == {"endpoint": 2, "hairpin": 2}
    # Both groups project to the same [0, 6] per-axis ranges; b is still excluded.
    assert [[n["conditional_preparations"] for n in a["nodes"]] for a in result["axes"]] == [
        [1, 1],
        [1, 1],
    ]
    conditioned = project_choices(
        index(), load_query(restricted("a", "c", parameters=[{"key": "left_gap", "values": [0]}]))
    )
    assert [p["materialized_realization_id"] for p in conditioned["paths"] if p["matches"]] == ["a"]
    assert [n["conditional_preparations"] for n in conditioned["axes"][1]["nodes"]] == [0, 1]


def test_empty_membership_stays_empty_and_wrong_snapshot_or_members_fail():
    assert project_choices(index(), load_query(restricted()))["matching_preparations"] == 0
    for raw, message in (
        (restricted("not-recorded"), "Unknown.*preparation"),
        (
            {"membership": {"snapshot_digest": "sha256:" + "b" * 64, "preparations": ["a"]}},
            "snapshot",
        ),
    ):
        with pytest.raises(ValueError, match=message):
            project_choices(index(), load_query(raw))
    with pytest.raises(ValueError, match="repeat"):
        load_query(restricted("a", "a"))


def test_default_query_bytes_are_unchanged_and_member_order_is_canonical():
    assert canonical_json_bytes(load_query(None)) == canonical_json_bytes(
        {"schema": "hop.interface-survey-query/v1", "parameters": []}
    )
    assert load_query(restricted("c", "a")) == load_query(restricted("a", "c"))


def test_family_query_intersects_existing_membership_and_preserves_parameters():
    choices = index()
    choices["paths"][1]["values"]["loop_nt"] = 6
    choices["query"] = json.loads(
        canonical_json_bytes(
            load_query(restricted("a", "b", parameters=[{"key": "left_gap", "values": [0]}]))
        )
    )
    families = molecular_families(choices, stage="hairpin")["families"]
    family = next(f for f in families if len(f["products"]) == 2)
    assert family["preparations"] == ["a", "c"]
    assert family["query"]["membership"] == {"snapshot_digest": DIGEST, "preparations": ["a"]}
    assert family["query"]["parameters"] == [
        {"key": "left_gap", "values": [0], "minimum": None, "maximum": None}
    ]
    assert project_choices(choices, load_query(family["query"]))["matching_preparations"] == 1


def test_search_cannot_expand_an_explicit_membership_filter():
    from hop_design.design.construction.variants.explanation import explain_choices

    result = project_choices(index(), load_query(restricted()))
    result["coverage"] = {"unresolved_pairs": 100}
    for axis in result["axes"]:
        axis["domain"] = {"basis": "observed_only"}
    answer = explain_choices(
        {"intent": {"product": "hairpin"}, "context": {"id": "test"}},
        result,
        can_continue=True,
    )
    assert "continue_search" not in answer["actions"]
    assert "membership" in answer["guidance"]
