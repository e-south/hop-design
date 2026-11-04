"""Assess actual molecular contrasts, never substitute drawing counts for products."""

import json

import pytest

from hop_design import construction
from tests.integration.test_scaffold_discovery import discovery_request, method_request


@pytest.fixture(scope="module")
def crossed_pool(tmp_path_factory):
    root = tmp_path_factory.mktemp("comparison-crossed")
    path = discovery_request(root)
    request = json.loads(path.read_bytes())
    request["product"]["foldback"]["geometry"]["loop_lengths_nt"] = [3, 4]
    request["scaffold"]["open_side_paired_positions"] = {"minimum": 17, "maximum": 18}
    path.write_text(json.dumps(request))
    packet = construction.discover_scaffolds(path)
    return request, packet.write(root / "pool")


def comparison(
    tmp_path, discovery, *, stage="hairpin", purpose="distinct_substrates", members=None
):
    discovery = json.loads(json.dumps(discovery))
    discovery["comparison_stage"] = stage
    path = tmp_path / "comparison.json"
    path.write_text(
        json.dumps(
            {
                "schema": "hop.comparison-brief/v1",
                "discovery": discovery,
                "purpose": purpose,
                "required_members": members
                if members is not None
                else [
                    {
                        "name": f"loop{loop}-open{extent}",
                        "dimensions": {
                            "loop_nt": loop,
                            "open_side_paired_positions": extent,
                        },
                    }
                    for loop in (3, 4)
                    for extent in (17, 18)
                ],
                "shared_properties": ["stem_sequence", "loop_side_paired_bp"],
                "preserve_material_roles": [],
                "max_group_evaluations": 100,
            }
        )
    )
    return path


def test_four_hairpins_cannot_satisfy_four_distinct_inserts(crossed_pool, tmp_path):
    request, pool = crossed_pool
    brief = comparison(tmp_path, request)
    packet = construction.assess_scaffold_comparison(brief, pool)
    hairpins = json.loads(packet.json_bytes)
    output = packet.write(tmp_path / "hairpin-comparison")
    assert 'data-region="open-side"' in (output / "pages/comparison-1.svg").read_text()
    assert hairpins["status"] == "comparison_available"
    assert len(hairpins["sets"]) == 1
    assert len(hairpins["sets"][0]["members"]) == 4
    assert hairpins["selected_set"] is None
    brief = comparison(tmp_path, request, stage="endpoint")
    packet = construction.assess_scaffold_comparison(brief, pool)
    inserts = json.loads(packet.json_bytes)
    assert inserts["status"] == "no_compatible_set_in_evaluated_pool"
    assert inserts["distinct_molecules"] == {"hairpin": 4, "endpoint": 2}
    assert inserts["group_coverage"]["rejections"]["repeated_molecular_substrate"] == 1
    assert inserts["sets"] == []
    assert all(m["option_labels"] for m in inserts["members"])
    assert "not a proof of global impossibility" in packet.report_text


def test_same_product_methods_retain_two_preparation_identities(tmp_path):
    path = method_request(tmp_path)
    discovery = json.loads(path.read_bytes())
    discovery["product"]["foldback"]["geometry"]["loop_lengths_nt"] = [3]
    path.write_text(json.dumps(discovery))
    pool = construction.discover_scaffolds(path).write(tmp_path / "methods")
    members = [
        {"name": name, "release_enzyme_id": f"example:enzyme/{slug}@1"}
        for name, slug in (("bsai", "bsai-hfv2"), ("bsmbi", "bsmbi-v2"))
    ]
    brief = comparison(
        tmp_path, discovery, stage="endpoint", purpose="preparation_alternatives", members=members
    )
    assessed = construction.assess_scaffold_comparison(brief, pool)
    output = assessed.write(tmp_path / "assessment")
    result = json.loads(assessed.json_bytes)
    assert result["status"] == "comparison_available"
    assert len(result["sets"]) == 1
    assert result["distinct_molecules"] == {"hairpin": 2, "endpoint": 1}
    assert (output / "report.pdf").read_bytes().startswith(b"%PDF")
    page = (output / "pages/comparison-1.svg").read_text()
    assert 'data-comparison-purpose="preparation_alternatives"' in page
    assert 'data-material-role="ligation_adapter"' in page
    assert "Common product" in page
    assert "BsmBI-v2" in page
    assert len(result["examined_failures"]) == 1
    assert result["examined_failures"][0]["rejection_reasons"] == [
        "clone-end-generation-incompatible"
    ]
    request = json.loads(brief.read_bytes())
    request["preserve_material_roles"] = ["ligation_adapter"]
    brief.write_text(json.dumps(request))
    result = json.loads(construction.assess_scaffold_comparison(brief, pool).json_bytes)
    assert result["sets"] == []
    assert result["status"] == "no_compatible_set_in_evaluated_pool"


def test_group_budget_and_member_order_are_explicit(crossed_pool, tmp_path):
    discovery, pool = crossed_pool
    brief = comparison(
        tmp_path,
        discovery,
        members=[
            {"name": "loop3", "dimensions": {"loop_nt": 3}},
            {"name": "loop4", "dimensions": {"loop_nt": 4}},
        ],
    )
    request = json.loads(brief.read_bytes())
    request["max_group_evaluations"] = 1
    brief.write_text(json.dumps(request))
    first = json.loads(construction.assess_scaffold_comparison(brief, pool).json_bytes)
    assert first["group_coverage"]["possible_assignments"] == 4
    assert first["group_coverage"]["evaluated_assignments"] == 1
    assert first["group_coverage"]["unexamined_assignments"] == 3
    assert len(first["sets"]) == 1
    request["required_members"].reverse()
    brief.write_text(json.dumps(request))
    second = json.loads(construction.assess_scaffold_comparison(brief, pool).json_bytes)
    assert first["sets"] == second["sets"]
    assert first["members"] == second["members"]


def test_assessment_rejects_changed_preparation_permissions(crossed_pool, tmp_path):
    discovery, pool = crossed_pool
    brief = comparison(tmp_path, discovery)
    request = json.loads(brief.read_bytes())
    request["discovery"]["preparation_changes"]["adapter_redesign"] = "preserve"
    brief.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="preparation permissions"):
        construction.assess_scaffold_comparison(brief, pool)
