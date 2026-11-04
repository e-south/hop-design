"""Further evaluation narrows the declared problem without Cartesian recombination."""

import json
from pathlib import Path

from hop_design.design.construction.discovery.branches import compile_branch_plan
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest


def request(parameters):
    value = json.loads(Path("examples/molecular-editing/request.json").read_bytes())
    value.update(
        schema="hop.scaffold-discovery/v5",
        parameters=parameters,
        end_placements=[{"left_bp": 0, "right_bp": 0}, {"left_bp": 6, "right_bp": 6}],
    )
    value["product"]["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[8, 9],
        junction_offsets_nt=[1, 2],
        loop_sequences=None,
    )
    return ScaffoldDiscoveryRequest.model_validate_json(json.dumps(value))


def test_restricting_derived_arm_targets_joint_geometry_before_search():
    branches, conflicts = compile_branch_plan(
        request(
            [
                {"key": "self_paired_arm_bp", "minimum": 7, "maximum": 7},
            ]
        )
    )
    assert not conflicts
    assert len(branches) == 4
    achieved = set()
    for branch in branches:
        p = branch["request"]
        f = p["foldback"]["geometry"]
        achieved.add((tuple(f["annealing_arm_lengths_bp"]), tuple(f["junction_offsets_nt"])))
        assert (
            p["ends"]["left"]["payload_end_offset_bp"],
            p["ends"]["right"]["payload_end_offset_bp"],
        ) in ((0, 0), (6, 6))
    assert achieved == {((8,), (1,)), ((9,), (2,))}


def test_empty_selection_is_a_scoped_conflict_and_never_expands_permissions():
    branches, conflicts = compile_branch_plan(
        request(
            [
                {"key": "left_gap", "values": [0]},
                {"key": "right_gap", "values": [6]},
            ]
        )
    )
    assert branches == []
    assert conflicts[0]["code"] == "parameter_domain_intersection_empty"
    assert conflicts[0]["scope"] == "declared_permissions_only"


def test_position_constraint_narrows_exact_bases_and_preserves_material_policy():
    value = request([{"key": "basal_source_base_2", "values": ["A", "G"]}])
    branches, conflicts = compile_branch_plan(value)
    assert not conflicts
    for branch in branches:
        assert branch["request"]["basal"]["geometry"]["pairing_constraints"][2][
            "allowed_source_bases"
        ] == ["A", "G"]
        assert (
            branch["request"]["materialization"]
            == value.product.model_dump(mode="json")["materialization"]
        )


def test_parameter_preview_retains_required_members_outside_this_evaluation_region(tmp_path):
    from hop_design import construction

    value = json.loads(Path("examples/molecular-editing/request.json").read_bytes())
    value.update(
        schema="hop.scaffold-discovery/v5",
        parameters=[{"key": "loop_word", "values": ["TTTC"]}],
        required_targets=[{"loop_sequence": "GAAA"}, {"loop_sequence": "TTTC"}],
    )
    value["product"]["foldback"]["geometry"]["loop_sequences"] = ["GAAA", "TTTC"]
    source = tmp_path / "targeted.json"
    source.write_text(json.dumps(value))
    preview = json.loads(construction.prepare_scaffold_discovery(source).json_bytes)
    assert preview["status"] == "ready"
    targets = {t["loop_sequence"]: t for t in preview["search_targets"]}
    assert targets["GAAA"]["parameter_scope"] == "outside_selected_region"
    assert targets["TTTC"].get("parameter_scope") != "outside_selected_region"
    assert all(
        b["request"]["foldback"]["geometry"]["loop_sequences"] == ["TTTC"]
        for b in preview["branches"]
    )
    # An actually contradictory intersection remains a readable negative preview.
    value["parameters"] = [{"key": "loop_word", "values": ["CCCC"]}]
    source.write_text(json.dumps(value))
    blocked = construction.prepare_scaffold_discovery(source)
    assert json.loads(blocked.json_bytes)["status"] == "conflicting_requirements"
    assert "Revise the selected constraints explicitly" in blocked.report_text
