"""Terminal shape is a requirement on the complete, recorded hairpin."""

import json
import shutil

import pytest

from hop_design import construction
from tests.integration.test_adapter_hairpin_endpoint import adapter_request


def terminal_request(tmp_path, five=6, three=14, *, permission="allow"):
    product = json.loads(adapter_request(tmp_path).read_bytes())
    product["foldback"]["geometry"].update(loop_lengths_nt=[3], annealing_arm_lengths_bp=[9])
    product["foldback"]["search"]["max_retained_overhead_nt"] = 32
    request = {
        "schema": "hop.scaffold-discovery/v2",
        "product": product,
        "scaffold": {
            "five_prime_unpaired_nt": {"minimum": five, "maximum": five},
            "three_prime_unpaired_nt": {"minimum": three, "maximum": three},
        },
        "preparation_changes": {"adapter_redesign": permission},
        "comparison_stage": "endpoint",
        "max_branches": 32,
        "max_continuations_per_branch": 1,
    }
    path = tmp_path / "terminals.json"
    path.write_text(json.dumps(request))
    return path


@pytest.mark.parametrize("five_prime,status", [(7, "complete"), (6, "infeasible")])
def test_terminal_requirements_check_the_complete_hairpin(tmp_path, five_prime, status):
    path = adapter_request(tmp_path)
    request = json.loads(path.read_bytes())
    request["whole_route_constraints"]["hairpin_scaffold"] = {
        "five_prime_unpaired_nt": {"minimum": five_prime, "maximum": five_prime},
        "three_prime_unpaired_nt": {"minimum": 14, "maximum": 14},
    }
    path.write_text(json.dumps(request))
    packet = construction.execute_construction_request(
        path, design_id="terminal-form", continuation="sole-witness"
    )
    result = json.loads(packet.json_bytes)
    assert result["status"] == status
    if status == "infeasible":
        assert result["scaffold_mismatches"][0]["dimension"] == "five_prime_unpaired_nt"
        assert result["scaffold_mismatches"][0]["observed"] == 7
        assert result["scope"] == "selected_combination"


@pytest.mark.parametrize("five,three,paired", [(6, 14, 18), (6, 8, 18), (6, 0, 18), (0, 0, 24)])
def test_discover_requested_terminal_forms_without_local_identifiers(tmp_path, five, three, paired):
    path = terminal_request(tmp_path, five, three)
    authored = path.read_bytes()
    prepared = construction.prepare_scaffold_discovery(path)
    preview = json.loads(prepared.json_bytes)
    assert preview["status"] == "ready"
    assert len(preview["branches"]) == 1
    branch = preview["branches"][0]
    assert branch["request"]["basal"]["geometry"]["minimum_adapter_annealing_nt"] == paired
    assert "5\u2032 unpaired" in prepared.report_text
    packet = construction.discover_scaffolds(path)
    result = json.loads(packet.json_bytes)
    assert len(result["options"]) == 1
    geometry = result["options"][0]["geometry"]
    assert geometry["five_prime_unpaired_nt"] == five
    assert geometry["three_prime_unpaired_nt"] == three
    assert geometry["open_side_paired_positions"] == paired
    assert path.read_bytes() == authored


@pytest.mark.parametrize("case", ["unsupported-endpoint", "tail-too-long", "paired-conflict"])
def test_terminal_preview_explains_conflicts_without_inventing_sequence(tmp_path, case):
    path = terminal_request(tmp_path, 0, 0)
    request = json.loads(path.read_bytes())
    if case == "unsupported-endpoint":
        # Reuse the valid duplex example; terminal translation initially targets
        # a requested adapter-ligated hairpin endpoint.
        from tests.integration.test_request_execution import request_path

        request["product"] = json.loads(request_path(tmp_path).read_bytes())
        expected = "product.endpoint"
    elif case == "tail-too-long":
        request["scaffold"]["three_prime_unpaired_nt"] = {"minimum": 20, "maximum": 20}
        expected = "product.materialization.adapter_ligation"
    else:
        request["scaffold"]["open_side_paired_positions"] = {"minimum": 18, "maximum": 18}
        expected = "scaffold.open_side_paired_positions"
    path.write_text(json.dumps(request))
    packet = construction.prepare_scaffold_discovery(path)
    result = json.loads(packet.json_bytes)
    assert result["status"] == "conflicting_requirements"
    assert result["branches"] == []
    assert any(c["inherited_field"] == expected for c in result["conflicts"])
    assert expected in packet.report_text


def test_terminal_family_retrieval_preserves_materials_and_portability(tmp_path):
    path = terminal_request(tmp_path, 0, 0)
    request = json.loads(path.read_bytes())
    request["scaffold"]["five_prime_unpaired_nt"] = {"minimum": 0, "maximum": 6}
    path.write_text(json.dumps(request))
    packet = construction.discover_scaffolds(path)
    pool = packet.write(tmp_path / "pool")
    result = json.loads(packet.json_bytes)
    assert len(result["options"]) == 7
    by_five = {o["geometry"]["five_prime_unpaired_nt"]: o for o in result["options"]}
    before, after = by_five[6]["material_roles"], by_five[0]["material_roles"]
    assert {r for r in before if before[r] != after[r]} == {"ligation_adapter"}
    selected = construction.select_scaffold_options(
        pool,
        members={"overhang": by_five[6]["label"], "paired": by_five[0]["label"]},
        baseline="overhang",
        shared_properties=("three_prime_unpaired_nt", "loop_nt"),
        compared_properties=("five_prime_unpaired_nt", "open_side_paired_positions"),
    )
    output = selected.write(tmp_path / "selected")
    drawing = (output / "pages/terminal-forms-1.svg").read_text()
    assert "5\u2032 6 nt" in drawing and "5\u2032 0 nt" in drawing
    assert "data-terminal-index=" in drawing
    assert "Adapter" in drawing
    assert "assembly compatibility" in drawing
    shutil.move(output, tmp_path / "relocated")
    retrieved = construction.select_construction_set(tmp_path / "relocated/set.json")
    assert retrieved.json_bytes == selected.json_bytes
    regenerated = retrieved.write(tmp_path / "retrieved")
    assert (regenerated / "pages/terminal-forms-1.svg").is_file()
    assert (regenerated / "report.pdf").read_bytes().startswith(b"%PDF")


def test_terminal_preserve_permission_keeps_adapter_and_returns_achieved_mismatch(tmp_path):
    path = terminal_request(tmp_path, 0, 0, permission="preserve")
    preview = json.loads(construction.prepare_scaffold_discovery(path).json_bytes)
    assert preview["branches"][0]["changes"] == []
    result = json.loads(construction.discover_scaffolds(path).json_bytes)
    assert result["options"] == []
    mismatches = result["branches"][0]["failures"][0]["scaffold_mismatches"]
    assert {m["dimension"] for m in mismatches} == {
        "five_prime_unpaired_nt",
        "three_prime_unpaired_nt",
    }


def test_declared_tail_is_exact_and_v1_cannot_silently_adopt_terminal_translation(tmp_path):
    path = terminal_request(tmp_path, 6, 20)
    request = json.loads(path.read_bytes())
    request["preparation_changes"]["three_prime_tail_sequences"] = ["ACTG" * 5]
    path.write_text(json.dumps(request))
    preview = json.loads(construction.prepare_scaffold_discovery(path).json_bytes)
    assert (
        preview["branches"][0]["request"]["materialization"]["adapter_ligation"][
            "three_prime_handle_sequence"
        ]
        == "ACTG" * 5
    )
    request["schema"] = "hop.scaffold-discovery/v1"
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError, match=r"requires hop\.scaffold-discovery/v2"):
        construction.prepare_scaffold_discovery(path)
