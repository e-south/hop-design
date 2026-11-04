"""Comparison intentions remain explicit before molecular execution."""

import json

import pytest

from hop_design import construction
from tests.integration.test_request_execution import hairpin_request
from tests.integration.test_scaffold_discovery import discovery_request


def brief_path(tmp_path, *, members=()):
    discovery = json.loads(discovery_request(tmp_path).read_bytes())
    discovery["scaffold"]["loop_nt"] = {"minimum": 3, "maximum": 8}
    path = tmp_path / "comparison.json"
    path.write_text(
        json.dumps(
            {
                "schema": "hop.comparison-brief/v1",
                "discovery": discovery,
                "purpose": "distinct_substrates",
                "required_members": list(members),
                "shared_properties": ["stem_sequence"],
                "preserve_material_roles": [],
                "max_group_evaluations": 100,
            }
        )
    )
    return path


def test_preview_distinguishes_permissions_from_required_members(tmp_path):
    path = brief_path(tmp_path)
    packet = construction.prepare_scaffold_comparison(path)
    allowed = json.loads(packet.json_bytes)
    assert allowed["required_members"] == []
    assert allowed["dimensions"]["loop_nt"]["effective_values"] == [3, 4, 6, 8]
    assert allowed["dimensions"]["loop_nt"]["excluded_intervals"] == [
        {"minimum": 5, "maximum": 5},
        {"minimum": 7, "maximum": 7},
    ]
    path = brief_path(
        tmp_path, members=[{"name": f"loop{n}", "dimensions": {"loop_nt": n}} for n in range(3, 9)]
    )
    packet = construction.prepare_scaffold_comparison(path)
    required = json.loads(packet.json_bytes)
    assert [m["name"] for m in required["required_members"]] == [
        "loop3",
        "loop4",
        "loop5",
        "loop6",
        "loop7",
        "loop8",
    ]
    assert required["status"] == "conflicting_requirements"
    assert {c["member"] for c in required["conflicts"]} == {"loop5", "loop7"}
    assert all(
        c["inherited_field"] == "discovery.product.foldback.geometry.loop_lengths_nt"
        for c in required["conflicts"]
    )
    assert "Required members: 6" in packet.report_text
    assert "5, 7" in packet.report_text
    assert "discovery.product.foldback.geometry.loop_lengths_nt" in packet.report_text


def test_fixed_direct_hairpin_arms_are_visible_before_execution(tmp_path):
    product = json.loads(hairpin_request(tmp_path).read_bytes())
    path = brief_path(tmp_path)
    request = json.loads(path.read_bytes())
    request["discovery"]["product"] = product
    request["discovery"]["preparation_changes"] = {"adapter_redesign": "preserve"}
    path.write_text(json.dumps(request))
    packet = construction.prepare_scaffold_comparison(path)
    preview = json.loads(packet.json_bytes)
    assert preview["status"] == "conflicting_requirements"
    assert preview["dimensions"]["open_side_paired_positions"]["effective_values"] == [10]
    assert any(
        c["inherited_field"] == "discovery.product.hairpin_basal_component"
        for c in preview["conflicts"]
    )
    assert "Fixed direct-hairpin arms" in packet.report_text


@pytest.mark.parametrize(
    "field,value",
    [
        ("invented", True),
        ("max_group_evaluations", True),
        ("max_group_evaluations", 0),
        ("max_group_evaluations", 100001),
        ("max_sets", 0),
        ("preserve_material_roles", ["unrecorded"]),
    ],
)
def test_comparison_brief_rejects_unknown_or_unbounded_intent(tmp_path, field, value):
    path = brief_path(tmp_path)
    request = json.loads(path.read_bytes())
    request[field] = value
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError):
        construction.prepare_scaffold_comparison(path)


def test_required_method_outside_permissions_is_explained(tmp_path):
    path = brief_path(
        tmp_path,
        members=[
            {
                "name": "method",
                "release_enzyme_id": "example:enzyme/unpermitted@1",
            }
        ],
    )
    packet = construction.prepare_scaffold_comparison(path)
    preview = json.loads(packet.json_bytes)
    assert preview["status"] == "conflicting_requirements"
    assert any(c.get("member") == "method" for c in preview["conflicts"])
    assert "release" in packet.report_text


def test_preserved_material_roles_use_the_existing_handoff_vocabulary(tmp_path):
    path = brief_path(tmp_path)
    request = json.loads(path.read_bytes())
    request["preserve_material_roles"] = ["source_materialization_forward_primer"]
    path.write_text(json.dumps(request))
    summary = json.loads(construction.prepare_scaffold_comparison(path).json_bytes)
    assert summary["preserve_material_roles"] == ["source_materialization_forward_primer"]
