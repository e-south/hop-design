"""Product dimensions drive explicitly permitted preparations, never silent repair."""

import json
import shutil

import pytest

from hop_design import construction
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.integration.test_request_execution import request_path


def discovery_request(tmp_path, *, adapter_redesign="allow"):
    product = json.loads(request_path(tmp_path).read_bytes())
    product["foldback"]["geometry"].update(
        loop_lengths_nt=[3, 4, 6, 8], annealing_arm_lengths_bp=[9]
    )
    product["foldback"]["search"].update(
        max_retained_overhead_nt=32, max_realizations=8, result_quota=8
    )
    mapping = {
        "schema": "hop.scaffold-discovery/v1",
        "product": product,
        "scaffold": {"open_side_paired_positions": {"minimum": 18, "maximum": 18}},
        "preparation_changes": {"adapter_redesign": adapter_redesign},
        "comparison_stage": "hairpin",
        "max_branches": 8,
        "max_continuations_per_branch": 8,
    }
    path = tmp_path / "discovery.json"
    path.write_text(json.dumps(mapping))
    return path


def test_preview_expands_product_dimension_only_with_permission(tmp_path):
    path = discovery_request(tmp_path)
    authored = path.read_bytes()
    packet = construction.prepare_scaffold_discovery(path)
    preview = json.loads(packet.json_bytes)
    assert preview["status"] == "ready"
    assert preview["comparison_stage"] == "hairpin"
    assert (
        preview["branches"][0]["request"]["basal"]["geometry"]["minimum_adapter_annealing_nt"] == 18
    )
    assert preview["branches"][0]["request"]["whole_route_constraints"]["hairpin_scaffold"][
        "open_side_paired_positions"
    ] == {"minimum": 18, "maximum": 18}
    assert preview["branches"][0]["changes"][0]["before"] == 17
    assert "achieved" in packet.report_text
    assert path.read_bytes() == authored


def test_preserve_permission_keeps_preparation_settings(tmp_path):
    path = discovery_request(tmp_path, adapter_redesign="preserve")
    preview = json.loads(construction.prepare_scaffold_discovery(path).json_bytes)
    branch = preview["branches"][0]
    assert branch["request"]["basal"]["geometry"]["minimum_adapter_annealing_nt"] == 17
    assert branch["changes"] == []


@pytest.mark.parametrize("conflict", ["inherited", "loop-domain", "fixed-adapter"])
def test_preview_explains_conflicts_without_erasing_requirements(tmp_path, conflict):
    path = discovery_request(tmp_path)
    request = json.loads(path.read_bytes())
    if conflict == "inherited":
        request["product"]["whole_route_constraints"]["hairpin_scaffold"] = {
            "open_side_paired_positions": {"minimum": 17, "maximum": 17}
        }
        expected = "product.whole_route_constraints.hairpin_scaffold.open_side_paired_positions"
    elif conflict == "loop-domain":
        request["scaffold"]["loop_nt"] = {"minimum": 5, "maximum": 5}
        expected = "product.foldback.geometry.loop_lengths_nt"
    else:
        request["product"]["materialization"]["endpoint_auxiliaries"]["adapter"] = {
            "mode": "fixed",
            "material": {
                "sequence_5prime": "ACGTACGTACGTACGTACGTACGTACGTACGT",
                "five_prime_end": "phosphate",
                "three_prime_end": "hydroxyl",
            },
        }
        expected = "product.materialization.endpoint_auxiliaries.adapter"
    path.write_text(json.dumps(request))
    packet = construction.prepare_scaffold_discovery(path)
    preview = json.loads(packet.json_bytes)
    assert preview["status"] == "conflicting_requirements"
    assert preview["branches"] == []
    assert preview["conflicts"][0]["inherited_field"] == expected
    assert preview["conflicts"][0]["requested_field"]
    assert preview["conflicts"][0]["explicit_edit"]
    assert expected in packet.report_text
    if conflict == "loop-domain":
        assert preview["conflicts"][0]["inherited_value"] == [3, 4, 6, 8]


def test_preview_accounts_for_nick_to_stem_span(tmp_path):
    path = discovery_request(tmp_path)
    request = json.loads(path.read_bytes())
    request["product"]["basal"]["geometry"]["nick_offsets_nt"] = [2]
    path.write_text(json.dumps(request))
    preview = json.loads(construction.prepare_scaffold_discovery(path).json_bytes)
    assert (
        preview["branches"][0]["request"]["basal"]["geometry"]["minimum_adapter_annealing_nt"] == 16
    )


@pytest.mark.parametrize("permission", ["allow", "preserve"])
def test_discovery_evaluates_achieved_geometry_and_retains_failure(tmp_path, permission):
    path = discovery_request(tmp_path, adapter_redesign=permission)
    packet = construction.discover_scaffolds(path)
    packet.write(tmp_path / "discovered")
    result = json.loads(packet.json_bytes)
    assert result["coverage"]["evaluated_branches"] == 1
    assert result["coverage"]["unexamined_branches"] == 0
    assert result["selected_options"] == []
    if permission == "allow":
        assert len(result["options"]) == 4
        assert {o["geometry"]["loop_nt"] for o in result["options"]} == {3, 4, 6, 8}
        assert {o["geometry"]["open_side_paired_positions"] for o in result["options"]} == {18}
    else:
        assert result["options"] == []
        mismatch = result["branches"][0]["failures"][0]["scaffold_mismatches"][0]
        assert mismatch["observed"] == 17
        assert mismatch["required"] == {"minimum": 18, "maximum": 18}
        assert "17" in packet.report_text and "18" in packet.report_text
        assert "hairpin-scaffold-outside-request" in packet.report_text
    assert (tmp_path / "discovered/report.pdf").read_bytes().startswith(b"%PDF")


@pytest.fixture(scope="module")
def discovered(tmp_path_factory):
    root = tmp_path_factory.mktemp("product-driven-discovery")
    packet = construction.discover_scaffolds(discovery_request(root))
    path = packet.write(root / "discovered")
    return path, json.loads(packet.json_bytes)


def test_named_selection_is_portable_and_preserves_exact_membership(discovered, tmp_path):
    path, result = discovered
    members = {f"loop{o['geometry']['loop_nt']}": o["label"] for o in result["options"]}
    packet = construction.select_scaffold_options(
        path,
        members=members,
        baseline="loop3",
        shared_properties=("open_side_paired_positions", "non_loop_sequences"),
        compared_properties=("loop_nt",),
    )
    output = packet.write(tmp_path / "selected")
    summary = json.loads(packet.json_bytes)
    assert [m["name"] for m in summary["members"]] == list(members)
    assert "loop3" in (output / "oligo-uses.csv").read_text()
    assert "loop3" in (output / "pages/comparison-1.svg").read_text()
    binding = json.loads((output / "discovery-selection.json").read_bytes())
    assert binding["members"] == members
    shutil.move(output, tmp_path / "relocated")
    replayed = construction.select_construction_set(tmp_path / "relocated/set.json")
    assert replayed.json_bytes == packet.json_bytes


def test_resealed_discovery_summary_cannot_change_membership(discovered, tmp_path):
    source, result = discovered
    path = tmp_path / "edited"
    shutil.copytree(source, path)
    result = json.loads(json.dumps(result))
    result["options"][0]["geometry"]["open_side_paired_positions"] = 99
    (path / "summary.json").write_bytes(canonical_json_bytes(result))
    manifest = json.loads((path / "manifest.json").read_bytes())
    manifest["artifacts"]["summary.json"] = sha256_digest((path / "summary.json").read_bytes())
    (path / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ValueError, match="disagrees"):
        construction.select_scaffold_options(
            path, members={"loop3": result["options"][0]["label"]}, baseline="loop3"
        )


def test_cli_previews_discovers_and_retrieves_named_options(tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app

    path = discovery_request(tmp_path)
    mapping = json.loads(path.read_bytes())
    mapping["max_continuations_per_branch"] = 1
    path.write_text(json.dumps(mapping))
    runner = CliRunner()
    preview = runner.invoke(
        app, ["construction", "preview-scaffolds", str(path), "--out", str(tmp_path / "preview")]
    )
    assert preview.exit_code == 0, preview.output
    discovery = runner.invoke(
        app, ["construction", "discover-scaffolds", str(path), "--out", str(tmp_path / "options")]
    )
    assert discovery.exit_code == 0, discovery.output
    result = json.loads((tmp_path / "options/summary.json").read_bytes())
    assert result["coverage"]["unexamined_pairs"] == 3
    label = result["options"][0]["label"]
    args = [
        "construction",
        "select-scaffolds",
        str(tmp_path / "options"),
        "--member",
        f"loop3={label}",
        "--baseline",
        "loop3",
        "--out",
        str(tmp_path / "selected"),
    ]
    selection = runner.invoke(app, args)
    assert selection.exit_code == 0, selection.output
    assert "loop3" in (tmp_path / "selected/oligo-uses.csv").read_text()
    assert runner.invoke(app, args).exit_code != 0


def method_request(tmp_path):
    path = discovery_request(tmp_path)
    request = json.loads(path.read_bytes())
    request["scaffold"]["open_side_paired_positions"] = {"minimum": 17, "maximum": 17}
    catalog = request["product"]["enzyme_catalog"]["enzymes"]
    base = next(e for e in catalog if e["canonical_name"] == "BsaI-HFv2")
    # Public manufacturer definitions; offsets are relative to recognition start.
    # https://www.neb.com/en-us/tools-and-resources/selection-charts/alphabetized-list-of-recognition-specificities
    for name, slug, motif, cut in (
        ("BsmBI-v2", "bsmbi-v2", "CGTCTC", 7),
        ("BbsI-HF", "bbsi-hf", "GAAGAC", 8),
    ):
        catalog.append(
            {
                **base,
                "enzyme_id": f"example:enzyme/{slug}@1",
                "canonical_name": name,
                "recognition_pattern": motif,
                "cut_offset_reference_strand": cut,
                "cut_offset_complement_strand": cut + 4,
            }
        )
    request["preparation_changes"]["release_enzyme_ids"] = [
        base["enzyme_id"],
        "example:enzyme/bsmbi-v2@1",
        "example:enzyme/bbsi-hf@1",
    ]
    path.write_text(json.dumps(request))
    return path


def test_method_preview_keeps_one_enzyme_per_executable_branch(tmp_path):
    path = method_request(tmp_path)
    preview = json.loads(construction.prepare_scaffold_discovery(path).json_bytes)
    assert preview["bounds"]["permitted_branches"] == 3
    branches = preview["branches"]
    assert [b["release_enzyme_id"] for b in branches] == [
        "example:enzyme/bsai-hfv2@1",
        "example:enzyme/bsmbi-v2@1",
        "example:enzyme/bbsi-hf@1",
    ]
    for branch in branches:
        product = branch["request"]
        enzyme = branch["release_enzyme_id"]
        assert product["release"]["enzymes"]["allowed_enzyme_ids"] == [enzyme]
        role = next(
            r
            for r in product["basal"]["enzymes"]["role_restrictions"]
            if r["role"] == "end_generation"
        )
        assert role["allowed_enzyme_ids"] == [enzyme]


def test_method_discovery_retains_rejected_continuations_and_budget(tmp_path):
    path = method_request(tmp_path)
    packet = construction.discover_scaffolds(path)
    full = json.loads(packet.json_bytes)
    assert [b["complete_preparations"] for b in full["branches"]] == [4, 4, 0]
    assert len(full["branches"][2]["failures"]) == 4
    assert full["branches"][2]["failures"][0]["rejection_reasons"] == [
        "clone-end-generation-incompatible"
    ]
    request = json.loads(path.read_bytes())
    request["max_branches"] = 1
    path.write_text(json.dumps(request))
    limited = json.loads(construction.discover_scaffolds(path).json_bytes)
    assert limited["coverage"]["unexamined_branches"] == 2
    assert limited["options"] == full["options"][:4]


def test_stage_grouping_distinguishes_hairpins_from_shared_released_products(tmp_path):
    path = discovery_request(tmp_path)
    request = json.loads(path.read_bytes())
    request["scaffold"]["open_side_paired_positions"] = {"minimum": 17, "maximum": 18}
    request["comparison_stage"] = "endpoint"
    path.write_text(json.dumps(request))
    packet = construction.discover_scaffolds(path)
    result = json.loads(packet.json_bytes)
    assert len(result["options"]) == 8
    assert len(result["molecules"]) == 4
    assert all(len(m["option_labels"]) == 2 for m in result["molecules"])
    assert len(result["stage_groups"]["hairpin"]) == 8
    assert len(result["stage_groups"]["endpoint"]) == 4
    for loop in (3, 4, 6, 8):
        options = [o for o in result["options"] if o["geometry"]["loop_nt"] == loop]
        assert (
            options[0]["molecular_identity"]["endpoint"]
            == options[1]["molecular_identity"]["endpoint"]
        )
        assert (
            options[0]["molecular_identity"]["hairpin"]
            != options[1]["molecular_identity"]["hairpin"]
        )
    assert "4 distinct" in packet.report_text
    assert "8 complete preparations" in packet.report_text
    output = packet.write(tmp_path / "stages")
    plate = (output / "pages/discovery-1.svg").read_text()
    assert "Same released duplex insert" in plate
    assert "Adapter" in plate
    assert "Open-side pairing" in plate
    assert 'data-molecule-stage="endpoint"' in plate
    chosen = [o for o in result["options"] if o["geometry"]["loop_nt"] == 3]
    selected = construction.select_scaffold_options(
        output,
        members={"short": chosen[0]["label"], "long": chosen[1]["label"]},
        baseline="short",
        compared_properties=("open_side_paired_positions",),
    )
    target = selected.write(tmp_path / "selected-stages")
    comparison = json.loads((target / "stage-comparison.json").read_bytes())
    assert comparison["comparison_stage"] == "endpoint"
    assert len(comparison["stage_groups"]["endpoint"]) == 1
    assert len(comparison["stage_groups"]["hairpin"]) == 2
    selected_svg = (target / "pages/stage-comparison-1.svg").read_text()
    assert "short" in selected_svg and "long" in selected_svg
    assert "none selected" not in selected_svg
