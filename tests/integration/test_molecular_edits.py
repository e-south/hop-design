"""Molecular edits preserve the original request and expose its effective constraints."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.serialization import canonical_json_bytes, sha256_digest


def loop_request(tmp_path):
    value = json.loads(Path("examples/scaffold-discovery/request.json").read_bytes())
    value["product"]["foldback"]["geometry"].update(loop_lengths_nt=[4], loop_sequences=["GAAA"])
    value["max_branches"] = 2
    path = tmp_path / "base.json"
    path.write_text(json.dumps(value))
    return path


def test_loop_edit_preview_preserves_original_and_unedited_permissions(tmp_path):
    path = loop_request(tmp_path)
    original = path.read_bytes()
    packet = construction.author_molecular_edit(path, loop_sequences=("GAAA", "TTTC"))
    out = packet.write(tmp_path / "edit")
    summary = json.loads(packet.json_bytes)
    compiled = json.loads((out / "compiled-request.json").read_bytes())
    assert summary["status"] == "ready"
    assert summary["execution"] == "not_started"
    assert compiled["product"]["foldback"]["geometry"]["loop_sequences"] == ["GAAA", "TTTC"]
    assert {t["loop_sequence"] for t in compiled["required_targets"]} == {"GAAA", "TTTC"}
    for name in ("materialization", "basal", "release", "ends", "whole_route_constraints"):
        # Default insertion is irrelevant to the user's authored values.
        authored = json.loads(original)["product"][name]
        assert all(compiled["product"][name][key] == val for key, val in authored.items())
    assert path.read_bytes() == original
    assert construction.prepare_molecular_edit(out / "edit.json").json_bytes == packet.json_bytes


def test_loop_edit_reports_inherited_length_conflict_before_search(tmp_path):
    path = loop_request(tmp_path)
    packet = construction.author_molecular_edit(path, loop_sequences=("TTC",))
    summary = json.loads(packet.json_bytes)
    assert summary["status"] == "conflicting_requirements"
    assert summary["execution"] == "not_started"
    assert any("loop" in str(c).lower() for c in summary["conflicts"])


def test_edit_rejects_changed_base_and_wrong_molecular_stage(tmp_path):
    path = loop_request(tmp_path)
    out = construction.author_molecular_edit(path, loop_sequences=("TTTC",)).write(
        tmp_path / "edit"
    )
    edit_path = out / "edit.json"
    original = json.loads(edit_path.read_bytes())
    value = json.loads(edit_path.read_bytes())
    value["original_request"]["product"]["stem_arm"] = "ACGT"
    edit_path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="original request digest"):
        construction.prepare_molecular_edit(edit_path)
    original["edits"][0]["stage"] = "released_insert"
    edit_path.write_text(json.dumps(original))
    with pytest.raises(ValueError, match="stage"):
        construction.prepare_molecular_edit(edit_path)


def test_loop_edit_evaluates_complete_molecules_and_retrieves_after_relocation(tmp_path):
    path = loop_request(tmp_path)
    edit = construction.author_molecular_edit(path, loop_sequences=("GAAA", "TTTC"))
    authored = edit.write(tmp_path / "intent")
    evaluated = construction.execute_molecular_edit(authored / "edit.json")
    root = evaluated.write(tmp_path / "evaluated")
    summary = json.loads(evaluated.json_bytes)
    assert len(summary["options"]) == 2
    assert summary["coverage"]["unexamined_branches"] >= 1
    assert (root / "report.pdf").read_bytes().startswith(b"%PDF")
    names = {}
    outside = []
    for option in summary["options"]:
        for relative in option["selection"].values():
            assert (root / relative).exists()
        view = json.loads((root / option["sequence_view"]).read_bytes())
        loop = next(r for r in view["regions"] if r["region"] == "loop")
        names[loop["observed_sequence"].lower()] = option["label"]
        outside.append([r["observed_sequence"] for r in view["regions"] if r["region"] != "loop"])
        assert view["portrait"]["stage_role"] == "intermediate"
    assert set(names) == {"gaaa", "tttc"}
    assert outside[0] == outside[1]
    for branch in summary["branches"]:
        assert (root / branch["report"]).is_file()
        assert (root / branch["request"]).is_file()
        for failure in branch["failures"]:
            assert (root / failure["outcome"]).is_file()
    moved = tmp_path / "moved"
    shutil.move(root, moved)
    selected = construction.select_molecular_edit(
        moved,
        edit_digest=summary["edit_digest"],
        members=names,
        baseline="gaaa",
        shared_properties=("non_loop_sequences", "regional_contacts", "terminal_chemistry"),
    )
    retrieved = selected.write(tmp_path / "selected")
    assert (retrieved / "oligos.csv").is_file()
    comparison = json.loads((retrieved / "comparisons/tttc.json").read_bytes())
    assert set(comparison["changed_material_roles"]) == {
        "source_ssdna",
        "source_materialization_reverse_primer",
    }
    replay = construction.select_construction_set(retrieved / "set.json")
    assert json.loads(replay.json_bytes)["set_id"] == json.loads(selected.json_bytes)["set_id"]
    with pytest.raises(ValueError, match=r"stale|digest"):
        construction.select_molecular_edit(
            moved, edit_digest="sha256:" + "0" * 64, members=names, baseline="gaaa"
        )
    view_path = summary["options"][1]["sequence_view"]
    view = json.loads((moved / view_path).read_bytes())
    view["changed_material_roles"] = []
    (moved / view_path).write_bytes(canonical_json_bytes(view))
    manifest = json.loads((moved / "manifest.json").read_bytes())
    manifest["artifacts"][view_path] = sha256_digest((moved / view_path).read_bytes())
    (moved / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ValueError, match="sequence view"):
        construction.select_molecular_edit(
            moved, edit_digest=summary["edit_digest"], members=names, baseline="gaaa"
        )


def test_conflicting_edit_cannot_start_execution(tmp_path):
    edit = construction.author_molecular_edit(loop_request(tmp_path), loop_sequences=("TTC",))
    root = edit.write(tmp_path / "edit")
    with pytest.raises(ValueError, match="Conflict"):
        construction.execute_molecular_edit(root / "edit.json")


def test_hairpin_endpoint_drawing_does_not_promise_a_later_released_product(tmp_path):
    path = loop_request(tmp_path)
    value = json.loads(path.read_bytes())
    product = value["product"]
    product.update(endpoint="adapter_ligated_hairpin", ends=None, release=None)
    auxiliaries = product["materialization"].pop("endpoint_auxiliaries")
    product["materialization"]["adapter_ligation"] = auxiliaries["adapter"]
    path.write_text(json.dumps(value))
    edit = construction.author_molecular_edit(path, loop_sequences=("GAAA",))
    authored = edit.write(tmp_path / "intent")
    evaluated = construction.execute_molecular_edit(authored / "edit.json")
    files = dict(evaluated._files)
    summary = json.loads(evaluated.json_bytes)
    assert summary["options"]
    drawing = files[summary["options"][0]["sequence_drawing"]].decode()
    assert "Hairpin endpoint" in drawing
    assert "Released ends belong to the later product" not in drawing


def test_cli_authors_the_same_edit_as_the_api(tmp_path):
    path = loop_request(tmp_path)
    out = tmp_path / "cli"
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "prepare-edit",
            str(path),
            "--loop",
            "GAAA",
            "--loop",
            "TTTC",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    api = construction.author_molecular_edit(path, loop_sequences=("GAAA", "TTTC"))
    assert (out / "summary.json").read_bytes() == api.json_bytes
