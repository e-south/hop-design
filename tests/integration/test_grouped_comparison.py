"""A scaffold-by-method set preserves equality within, and difference between, groups."""

import json
import shutil
from pathlib import Path

import pytest

from hop_design import construction
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.support.grouped_comparison import create_method_pool, grouped_brief


@pytest.fixture(scope="module")
def method_pool(tmp_path_factory):
    return create_method_pool(tmp_path_factory.mktemp("grouped-methods"))


def test_grouped_products_select_replay_and_relocate(method_pool, tmp_path):
    discovery, pool = method_pool
    path = grouped_brief(tmp_path, discovery)
    preview = json.loads(construction.prepare_scaffold_comparison(path).json_bytes)
    assert preview["status"] == "ready"
    assert [g["name"] for g in preview["groups"]] == ["loop3", "loop4"]
    assessed = construction.assess_scaffold_comparison(path, pool)
    summary = json.loads(assessed.json_bytes)
    assert summary["status"] == "comparison_available"
    assert summary["distinct_molecules"] == {"hairpin": 4, "endpoint": 2}
    assert len(summary["sets"]) == 1
    chosen = summary["sets"][0]
    identities = chosen["molecular_identities"]
    assert identities["loop3-bsai"] == identities["loop3-bsmbi"]
    assert identities["loop4-bsai"] == identities["loop4-bsmbi"]
    assert identities["loop3-bsai"] != identities["loop4-bsai"]
    output = assessed.write(tmp_path / "assessment")
    moved = tmp_path / "relocated"
    shutil.copytree(output, moved)
    first = construction.select_scaffold_comparison(
        output, set_label="set-0001", baseline="loop3-bsai"
    )
    second = construction.select_scaffold_comparison(
        moved, set_label="set-0001", baseline="loop3-bsai"
    )
    assert first.json_bytes == second.json_bytes
    assert dict(first._files)["oligos.csv"] == dict(second._files)["oligos.csv"]
    selected = first.write(tmp_path / "selected")
    selection = json.loads((selected / "comparison-selection.json").read_bytes())
    assert selection["request"]["groups"] == preview["groups"]


def test_group_relationship_is_stage_specific_and_order_independent(method_pool, tmp_path):
    discovery, pool = method_pool
    path = grouped_brief(tmp_path, discovery)
    first = json.loads(construction.assess_scaffold_comparison(path, pool).json_bytes)
    request = json.loads(path.read_bytes())
    request["required_members"].reverse()
    request["groups"].reverse()
    for group in request["groups"]:
        group["members"].reverse()
    path.write_text(json.dumps(request))
    second = json.loads(construction.assess_scaffold_comparison(path, pool).json_bytes)
    assert first["sets"] == second["sets"]
    request["discovery"]["comparison_stage"] = "hairpin"
    path.write_text(json.dumps(request))
    hairpin = json.loads(construction.assess_scaffold_comparison(path, pool).json_bytes)
    assert hairpin["sets"] == []
    assert hairpin["group_coverage"]["rejections"] == {"different_products_within_group": 1}
    for purpose in ("distinct_substrates", "preparation_alternatives"):
        request.pop("groups", None)
        request.pop("between_groups", None)
        request.update(schema="hop.comparison-brief/v1", purpose=purpose)
        request["discovery"]["comparison_stage"] = "endpoint"
        path.write_text(json.dumps(request))
        assert (
            json.loads(construction.assess_scaffold_comparison(path, pool).json_bytes)["sets"] == []
        )


@pytest.mark.parametrize(
    "mutation", ["unknown", "overlap", "missing", "empty", "duplicate", "contradictory"]
)
def test_group_membership_is_an_explicit_partition(method_pool, tmp_path, mutation):
    discovery, _ = method_pool
    path = grouped_brief(tmp_path, discovery)
    request = json.loads(path.read_bytes())
    if mutation == "unknown":
        request["groups"][0]["members"][0] = "absent"
    elif mutation == "overlap":
        request["groups"][1]["members"].append("loop3-bsai")
    elif mutation == "missing":
        request["groups"][0]["members"].pop()
    elif mutation == "empty":
        request["groups"][0]["members"] = []
    elif mutation == "duplicate":
        request["groups"][0]["members"].append("loop3-bsai")
    else:
        request["purpose"] = "distinct_substrates"
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError):
        construction.prepare_scaffold_comparison(path)


def test_grouped_sheet_shows_methods_converging_on_products(method_pool, tmp_path):
    discovery, pool = method_pool
    path = grouped_brief(tmp_path, discovery)
    packet = construction.assess_scaffold_comparison(path, pool)
    page = dict(packet._files)["pages/comparison-1.svg"].decode()
    assert 'data-comparison-purpose="grouped_substrates"' in page
    assert 'data-scaffold-group="loop3"' in page
    assert 'data-scaffold-group="loop4"' in page
    assert "BsaI-HFv2" in page and "BsmBI-v2" in page
    assert page.count('data-molecule-stage="endpoint"') == 2
    assert "Same product within each row" in page
    assert "What changes in making it" in page
    assert 'data-sequence-change="substitution"' in page
    assert "Released duplex insert" in page


def test_grouped_boundary_names_failed_method_and_actual_reference(tmp_path):
    request = json.loads(Path("examples/scaffold-comparison/grouped.json").read_bytes())
    request["discovery"]["preparation_changes"]["release_enzyme_ids"].append(
        "example:enzyme/bbsi-hf@1"
    )
    for group, loop in zip(request["groups"], (3, 4), strict=True):
        name = f"loop{loop}-bbsi"
        group["members"].append(name)
        request["required_members"].append(
            {
                "name": name,
                "dimensions": {"loop_nt": loop},
                "release_enzyme_id": "example:enzyme/bbsi-hf@1",
            }
        )
    path = tmp_path / "failed-method.json"
    path.write_text(json.dumps(request))
    packet = construction.execute_scaffold_comparison(path)
    summary = json.loads(packet.json_bytes)
    assert summary["sets"] == []
    opening = dict(packet._files)["pages/comparison-1.svg"].decode()
    assert "No complete requested set was found" in opening
    assert "loop3-bbsi" in opening and "missing from the evaluated pool" in opening
    page = next(
        data.decode()
        for name, data in packet._files
        if name.startswith("pages/") and b'data-comparison-purpose="grouped_substrates"' in data
    )
    assert "BbsI-HF" in page
    assert "example:enzyme/bbsi-hf@1" not in page
    assert "Sequence reference: loop3-bsai" in page
    assert "No verified common product" in page


def test_grouped_assignment_bounds_do_not_mean_no_release_method(method_pool, tmp_path):
    discovery, pool = method_pool
    path = grouped_brief(tmp_path, discovery)
    request = json.loads(path.read_bytes())
    request["required_members"] = [
        {"name": name, "dimensions": {"loop_nt": 3}} for name in ("first", "second")
    ]
    request["groups"] = [
        {"name": "loop3", "members": ["first", "second"], "product_relationship": "identical"}
    ]
    request["max_group_evaluations"] = 1
    path.write_text(json.dumps(request))
    limited = json.loads(construction.assess_scaffold_comparison(path, pool).json_bytes)
    assert limited["sets"] == []
    assert limited["group_coverage"]["unexamined_assignments"] == 3
    request["max_group_evaluations"] = 4
    path.write_text(json.dumps(request))
    complete = construction.assess_scaffold_comparison(path, pool)
    assert len(json.loads(complete.json_bytes)["sets"]) == 2
    page = dict(complete._files)["pages/comparison-1.svg"].decode()
    assert "Any permitted method" in page
    assert "No release method" not in page


def test_resealed_group_relationship_change_is_rejected(method_pool, tmp_path):
    discovery, pool = method_pool
    path = grouped_brief(tmp_path, discovery)
    output = construction.assess_scaffold_comparison(path, pool).write(tmp_path / "original")
    changed = tmp_path / "changed"
    shutil.copytree(output, changed)
    request = json.loads((changed / "request.json").read_bytes())
    first, second = request["groups"]
    first["members"][1], second["members"][1] = second["members"][1], first["members"][1]
    (changed / "request.json").write_bytes(canonical_json_bytes(request))
    manifest = json.loads((changed / "manifest.json").read_bytes())
    manifest["artifacts"]["request.json"] = sha256_digest((changed / "request.json").read_bytes())
    (changed / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ValueError, match=r"comparison.*disagrees"):
        construction.select_scaffold_comparison(
            changed, set_label="set-0001", baseline="loop3-bsai"
        )
