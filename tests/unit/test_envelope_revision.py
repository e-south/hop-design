"""Revising permissions is explicit; product and preservation intent survive."""

import json
from pathlib import Path

import pytest

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest


def seed():
    value = json.loads(Path("examples/molecular-editing/construction-envelope.json").read_bytes())
    value["product"]["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[8, 9, 10],
        loop_lengths_nt=[4],
        loop_sequences=["GAAA", "TTTC"],
        junction_offsets_nt=[1, 2, 3],
    )
    value["parameters"] = [{"key": "foldback_arm_bp", "minimum": 8, "maximum": 10}]
    return ScaffoldDiscoveryRequest.model_validate_json(json.dumps(value))


def test_open_geometry_and_sequences_preserve_the_molecular_problem():
    from hop_design.design.construction.variants.envelopes.revision import revise_request

    original = seed()
    revised, changes = revise_request(
        original,
        {
            "schema": "hop.scaffold-envelope-revision/v1",
            "changes": [
                {"path": "product.foldback.geometry.annealing_arm_lengths_bp", "value": []},
                {"path": "product.foldback.geometry.loop_lengths_nt", "value": []},
                {"path": "product.foldback.geometry.loop_sequences", "value": None},
                {"path": "product.foldback.geometry.junction_offsets_nt", "value": [1, 2, 3, 4, 5]},
                {"path": "parameters", "value": []},
            ],
        },
    )
    f = revised.product.foldback.geometry
    assert f.annealing_arm_lengths_bp == ()
    assert f.loop_lengths_nt == ()
    assert f.loop_sequences is None
    assert f.junction_offsets_nt == (1, 2, 3, 4, 5)
    assert revised.product.stem_arm == original.product.stem_arm
    assert revised.product.ends == original.product.ends
    assert revised.product.materialization == original.product.materialization
    assert revised.product.whole_route_constraints == original.product.whole_route_constraints
    assert revised.product.foldback.search == original.product.foldback.search
    assert len(changes) == 5
    assert changes[0]["before"] == [8, 9, 10]
    assert changes[0]["after"] == []


def test_explicit_arm_revision_opens_new_joint_solutions_for_a_preserved_derived_target():
    from hop_design.design.construction.discovery.branches import compile_branch_plan
    from hop_design.design.construction.variants.envelopes.revision import revise_request

    revised, _ = revise_request(
        seed(),
        {
            "schema": "hop.scaffold-envelope-revision/v1",
            "changes": [
                {
                    "path": "product.foldback.geometry.annealing_arm_lengths_bp",
                    "value": [10, 11, 12],
                },
                {"path": "parameters", "value": [{"key": "self_paired_arm_bp", "values": [9]}]},
            ],
        },
    )
    branches, conflicts = compile_branch_plan(revised)
    assert not conflicts
    assert {
        (
            tuple(b["request"]["foldback"]["geometry"]["annealing_arm_lengths_bp"]),
            tuple(b["request"]["foldback"]["geometry"]["junction_offsets_nt"]),
        )
        for b in branches
    } == {((10,), (1,)), ((11,), (2,)), ((12,), (3,))}


@pytest.mark.parametrize(
    "path,value",
    [
        ("product.stem_arm", "AAAA"),
        ("product.ends.left.cohesive_end_sequence", "AAAA"),
        ("product.materialization", {}),
        ("product.whole_route_constraints", {}),
        ("product.enzyme_catalog", {}),
        ("product.foldback.enzymes.forbidden_enzyme_ids", []),
        ("scaffold", None),
        ("unknown", 1),
    ],
)
def test_revision_cannot_smuggle_changes_to_locked_intent(path, value):
    from hop_design.design.construction.variants.envelopes.revision import revise_request

    with pytest.raises(ValueError, match="not an editable envelope field"):
        revise_request(
            seed(),
            {
                "schema": "hop.scaffold-envelope-revision/v1",
                "changes": [{"path": path, "value": value}],
            },
        )


def test_revision_validates_values_and_rejects_duplicate_field_edits():
    from hop_design.design.construction.variants.envelopes.revision import revise_request

    for changes in (
        [{"path": "product.foldback.geometry.loop_sequences", "value": ["NNNN"]}],
        [{"path": "product.foldback.geometry.annealing_arm_lengths_bp", "value": [-1]}],
        [{"path": "product.foldback.geometry.loop_sequences", "value": None}] * 2,
    ):
        with pytest.raises(ValueError):
            revise_request(
                seed(), {"schema": "hop.scaffold-envelope-revision/v1", "changes": changes}
            )
