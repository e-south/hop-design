"""Receiving ends are joint requested tuples, never independent menus."""

import copy
import json

import pytest

from hop_design import construction
from tests.integration.test_scaffold_discovery import discovery_request


def roster_request(tmp_path):
    path = discovery_request(tmp_path)
    value = json.loads(path.read_bytes())
    base = value["product"]["ends"]
    pairs = [copy.deepcopy(base) for _ in range(3)]
    pairs[1]["left"]["cohesive_end_sequence"] = "CATT"
    pairs[2]["right"]["cohesive_end_sequence"] = "AGCC"
    value.update(
        schema="hop.scaffold-discovery/v6",
        receiving_end_pairs=pairs,
        max_branches=3,
        max_continuations_per_branch=1,
    )
    value["product"]["foldback"]["geometry"].update(loop_lengths_nt=[4])
    path.write_text(json.dumps(value))
    return path, value


def test_preview_preserves_each_joint_pair_and_never_crosses_words(tmp_path):
    path, authored = roster_request(tmp_path)
    preview = json.loads(construction.prepare_scaffold_discovery(path).json_bytes)
    assert preview["status"] == "ready"
    assert len(preview["branches"]) == 3
    assert [b["request"]["ends"] for b in preview["branches"]] == authored["receiving_end_pairs"]
    assert all(
        any(c["permission"] == "receiving_end_pairs" for c in b["changes"])
        for b in preview["branches"]
    )
    assert json.loads(path.read_bytes()) == authored
    assert len({b["branch_id"] for b in preview["branches"]}) == 3


@pytest.mark.parametrize("defect", ["old_schema", "duplicate", "placements", "too_many", "empty"])
def test_roster_requires_explicit_finite_unambiguous_authority(tmp_path, defect):
    path, value = roster_request(tmp_path)
    if defect == "old_schema":
        value["schema"] = "hop.scaffold-discovery/v5"
    elif defect == "duplicate":
        value["receiving_end_pairs"].append(value["receiving_end_pairs"][0])
    elif defect == "placements":
        value["end_placements"] = [{"left_bp": 0, "right_bp": 0}]
    elif defect == "too_many":
        value["receiving_end_pairs"] *= 22
    else:
        value["receiving_end_pairs"] = []
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        construction.prepare_scaffold_discovery(path)


def test_complete_evaluation_retains_joint_authorities_and_negative_members(tmp_path):
    path, authored = roster_request(tmp_path)
    receipt = construction.discover_scaffolds(path)
    root = receipt.write(tmp_path / "outcomes")
    summary = json.loads(receipt.json_bytes)
    assert len(summary["branches"]) == 3
    requests = [json.loads((root / b["request"]).read_bytes())["ends"] for b in summary["branches"]]
    assert requests == authored["receiving_end_pairs"]
    assert summary["options"]
    assert any(not b["complete_preparations"] for b in summary["branches"])
    pool = construction.load_scaffold_exploration(root)
    choices = construction.query_scaffold_variants(
        pool,
        {
            "result_digest": pool.result_digest,
            "stage": "endpoint",
            "focus": "interfaces",
        },
    )
    facts = json.loads(choices.json_bytes)
    space = facts["choice_space"]
    assert space["joint_permissions"]["receiving_end_pairs"] == authored["receiving_end_pairs"]
    assert [b["receiving_end_pair"] for b in space["branch_coverage"]] == authored[
        "receiving_end_pairs"
    ]
    axes = {a["key"]: a for a in space["axes"]}
    assert axes["left_end_word"]["declared"]["values"] == ["AGTC", "CATT"]
    assert axes["right_end_word"]["declared"]["values"] == ["AGCC", "AGTC"]
    cross = construction.query_scaffold_variants(
        pool,
        {
            "schema": "hop.scaffold-variant-query/v2",
            "result_digest": pool.result_digest,
            "stage": "endpoint",
            "focus": "interfaces",
            "parameters": [
                {"key": "left_end_word", "values": ["CATT"]},
                {"key": "right_end_word", "values": ["AGCC"]},
            ],
        },
    )
    assert not json.loads(cross.json_bytes)["compatible_options"]
    with pytest.raises(ValueError, match=r"conflict|intersect|overlap"):
        construction.evaluate_scaffold_parameters(
            pool, cross, max_branches=1, max_continuations_per_branch=1
        )
