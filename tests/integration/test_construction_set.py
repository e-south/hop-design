"""A selected set preserves exact members and all chemical ordering identities."""

import csv
import json

import pytest

from hop_design import construction
from tests.integration.test_construction_comparison_projection import loop_series as loop_series


def set_path(tmp_path, loop_series):
    receipts, root = loop_series
    members = []
    for loop, receipt in zip((3, 4), receipts, strict=True):
        selection = construction.select_construction_realization(
            receipt, materialized_realization_id=receipt.materialized_realization_ids[0]
        )
        selection.write(tmp_path / f"loop{loop}.json")
        members.append(
            {
                "name": f"loop{loop}",
                "bundle_path": str(root / str(loop) / "execution/construction"),
                "selection_path": f"loop{loop}.json",
            }
        )
    request = {
        "schema": "hop.construction-set/v1",
        "members": members,
        "baseline": "loop3",
        "shared_properties": [
            "stem_sequence",
            "endpoint",
            "release_interfaces",
            "loop_side_paired_bp",
        ],
        "compared_properties": ["loop_nt"],
    }
    path = tmp_path / "set.json"
    path.write_text(json.dumps(request))
    return path


def test_select_set_keeps_chemical_identity_and_each_role_use(tmp_path, loop_series):
    path = set_path(tmp_path, loop_series)
    packet = construction.select_construction_set(path)
    data = json.loads(packet.json_bytes)
    assert data["schema"] == "hop.construction-set-summary/v2"
    assert [m["name"] for m in data["members"]] == ["loop3", "loop4"]
    assert data["baseline"] == "loop3"
    packet.write(tmp_path / "selected")
    rows = list(csv.DictReader((tmp_path / "selected/oligos.csv").open()))
    assert len(rows) == 7  # Three shared specifications plus two distinct source/primer pairs.
    uses = list(csv.DictReader((tmp_path / "selected/oligo-uses.csv").open()))
    assert len(uses) == 12  # Six required roles in each complete preparation.
    reverse = [u for u in uses if u["role"] == "source_materialization_reverse_primer"]
    by_id = {r["material_id"]: r for r in rows}
    assert all(by_id[u["material_id"]]["five_prime_end"] == "phosphate" for u in reverse)
    comparison = json.loads((tmp_path / "selected/comparisons/loop4.json").read_text())
    assert comparison["changed_material_roles"] == [
        "source_ssdna",
        "source_materialization_reverse_primer",
    ]
    # The exported membership is portable and can be selected again after relocation.
    restored = construction.select_construction_set(tmp_path / "selected/set.json")
    assert restored.json_bytes == packet.json_bytes


@pytest.mark.parametrize("fault", ["stale", "duplicate", "shared", "missing"])
def test_set_rejects_invalid_membership_without_partial_export(tmp_path, loop_series, fault):
    path = set_path(tmp_path, loop_series)
    data = json.loads(path.read_text())
    if fault == "stale":
        data["members"][1]["selection_path"] = "loop3.json"
    elif fault == "duplicate":
        data["members"][1] = {**data["members"][0], "name": "duplicate"}
    elif fault == "shared":
        data["shared_properties"].append("loop_nt")
    else:
        data["members"][1]["bundle_path"] = "missing-bundle"
    path.write_text(json.dumps(data))
    with pytest.raises((ValueError, FileNotFoundError)):
        construction.select_construction_set(path).write(tmp_path / "selected")
    assert not (tmp_path / "selected").exists()


def test_set_cli_and_api_export_the_same_selected_members(tmp_path, loop_series):
    from typer.testing import CliRunner

    from hop_design.cli import app

    path = set_path(tmp_path, loop_series)
    result = CliRunner().invoke(
        app, ["construction", "select-set", str(path), "--out", str(tmp_path / "cli")]
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "cli/summary.json").read_bytes() == construction.select_construction_set(
        path
    ).json_bytes


def test_set_output_cannot_modify_any_input_authority(tmp_path, loop_series):
    path = set_path(tmp_path, loop_series)
    packet = construction.select_construction_set(path)
    for member in json.loads(path.read_text())["members"]:
        from pathlib import Path

        output = Path(member["bundle_path"]) / "new" / "set"
        with pytest.raises(ValueError, match="outside"):
            packet.write(output)
        assert not output.parent.exists()


def test_same_scaffold_keeps_distinct_source_chemistry_in_order_table(tmp_path, loop_series):
    path = set_path(tmp_path, loop_series)
    _, root = loop_series
    request = json.loads((root / "3/request.json").read_text())
    request["materialization"]["source_preparation"]["source_ssdna"]["five_prime_end"] = "phosphate"
    new_request = tmp_path / "phosphate.json"
    new_request.write_text(json.dumps(request))
    construction.execute_construction_request(
        new_request, design_id="source-phosphate", continuation="sole-witness"
    ).write(tmp_path / "phosphate")
    receipt = construction.load_verified_construction_bundle(tmp_path / "phosphate/construction")
    construction.select_construction_realization(
        receipt, materialized_realization_id=receipt.materialized_realization_ids[0]
    ).write(tmp_path / "phosphate-selection.json")
    selected = json.loads(path.read_text())
    selected["members"][1] = {
        "name": "same-shape",
        "bundle_path": "phosphate/construction",
        "selection_path": "phosphate-selection.json",
    }
    selected["shared_properties"].append("loop_nt")
    selected["compared_properties"] = []
    path.write_text(json.dumps(selected))
    packet = construction.select_construction_set(path)
    packet.write(tmp_path / "chemistry-set")
    members = json.loads(packet.json_bytes)["members"]
    assert members[0]["properties"] == members[1]["properties"]
    assert members[0]["materialized_realization_id"] != members[1]["materialized_realization_id"]
    rows = list(csv.DictReader((tmp_path / "chemistry-set/oligos.csv").open()))
    uses = list(csv.DictReader((tmp_path / "chemistry-set/oligo-uses.csv").open()))
    source_ids = {r["material_id"] for r in uses if r["role"] == "source_ssdna"}
    sources = [r for r in rows if r["material_id"] in source_ids]
    assert len(sources) == 2
    assert len({r["sequence_5prime"] for r in sources}) == 1
    assert {r["five_prime_end"] for r in sources} == {"hydroxyl", "phosphate"}
    assert len(rows) == 6


def test_set_refuses_to_merge_different_product_stages(tmp_path, loop_series):
    from tests.integration.test_request_execution import hairpin_request

    path = set_path(tmp_path, loop_series)
    construction.execute_construction_request(
        hairpin_request(tmp_path), design_id="direct-member", continuation="sole-witness"
    ).write(tmp_path / "direct")
    receipt = construction.load_verified_construction_bundle(tmp_path / "direct/construction")
    construction.select_construction_realization(
        receipt, materialized_realization_id=receipt.materialized_realization_ids[0]
    ).write(tmp_path / "direct-selection.json")
    request = json.loads(path.read_text())
    request["members"][1] = {
        "name": "direct",
        "bundle_path": "direct/construction",
        "selection_path": "direct-selection.json",
    }
    request["shared_properties"] = []
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="same product stage and endpoint"):
        construction.select_construction_set(path).write(tmp_path / "mixed")
    assert not (tmp_path / "mixed").exists()


def test_set_refuses_a_corrupt_member_authority(tmp_path, loop_series):
    import shutil

    path = set_path(tmp_path, loop_series)
    request = json.loads(path.read_text())
    corrupt = tmp_path / "corrupt"
    shutil.copytree(request["members"][1]["bundle_path"], corrupt)
    manifest = corrupt / "construction-bundle.json"
    manifest.write_text(manifest.read_text().replace('"result_id":', '"unknown_result_id":', 1))
    request["members"][1]["bundle_path"] = "corrupt"
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError):
        construction.select_construction_set(path).write(tmp_path / "partial")
    assert not (tmp_path / "partial").exists()


@pytest.mark.parametrize("fault", ["missing", "misbound"])
def test_admitted_set_still_binds_each_exact_selection(tmp_path, loop_series, fault):
    from hop_design.design.construction.families.selection import (
        _select_admitted_construction_set,
    )
    from hop_design.models.construction.family.selection import ConstructionSetRequest

    path = set_path(tmp_path, loop_series)
    request = ConstructionSetRequest.model_validate_json(path.read_bytes())
    receipts, _ = loop_series
    admitted = dict(zip(("loop3", "loop4"), receipts, strict=True))
    if fault == "missing":
        del admitted["loop4"]
        message = "Admitted authorities must match"
    else:
        admitted["loop4"] = admitted["loop3"]
        message = "does not belong to this verified construction result"
    with pytest.raises(ValueError, match=message):
        _select_admitted_construction_set(path, request, admitted, ()).write(tmp_path / "partial")
    assert not (tmp_path / "partial").exists()


def test_standalone_set_rejects_first_selection_before_loading_later_members(
    tmp_path, loop_series, monkeypatch
):
    from hop_design.design.construction.families import set_members

    path = set_path(tmp_path, loop_series)
    request = json.loads(path.read_bytes())
    request["members"][0]["selection_path"] = "loop4.json"
    path.write_text(json.dumps(request))
    original = set_members.load_verified_construction_bundle
    admitted = []

    def observed(root):
        admitted.append(root)
        return original(root)

    monkeypatch.setattr(set_members, "load_verified_construction_bundle", observed)
    with pytest.raises(ValueError, match="does not belong to this verified construction result"):
        construction.select_construction_set(path)
    assert len(admitted) == 1


def test_standalone_set_admits_prior_material_reference_before_members(
    tmp_path, loop_series, monkeypatch
):
    from hop_design.design.construction.families import set_members
    from hop_design.models.construction.family.selection import ConstructionSetRequest

    path = set_path(tmp_path, loop_series)
    request = json.loads(path.read_bytes())
    request.update(
        schema="hop.construction-set/v2",
        reuse_prior_materials={
            "reference": {"bundle_path": "missing-prior", "selection_path": "prior.json"},
            "roles": ["source_ssdna"],
        },
    )
    path.write_text(json.dumps(request))
    ConstructionSetRequest.model_validate_json(path.read_bytes())
    admitted = []
    original = set_members.load_verified_construction_bundle

    def observed(root):
        admitted.append(root)
        return original(root)

    monkeypatch.setattr(set_members, "load_verified_construction_bundle", observed)
    with pytest.raises((ValueError, FileNotFoundError)):
        construction.select_construction_set(path)
    assert admitted == []
