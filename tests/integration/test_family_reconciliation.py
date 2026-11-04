"""Explicit continuation returns to a family without erasing its original boundary."""

import json

import pytest

from hop_design import construction
from tests.integration.test_construction_family import family_path


@pytest.fixture(scope="module")
def continued_family(tmp_path_factory):
    root = tmp_path_factory.mktemp("reconcile-family")
    path = family_path(root)
    request = json.loads(path.read_text())
    request["members"] = [{"name": "choices", "loop_side_paired_bp": 7}]
    request["base_request"]["foldback"]["search"].update(max_realizations=2, result_quota=2)
    path.write_text(json.dumps(request))
    construction.execute_construction_family(path, continuation="sole-witness").write(
        root / "saved"
    )
    member_request = root / "saved/members/choices/request.json"
    construction.prepare_construction_request(member_request).write(root / "prepared")
    selections = {}
    for local in ("foldback", "basal"):
        receipt = construction.discover_local_neighborhood(root / f"prepared/{local}.json")
        receipt.write(root / local)
        selections[local + "_path"] = root / f"{local}/result.json"
        selections[local + "_realization_id"] = construction.list_local_realizations(receipt)[
            -1
        ].realization_id
    construction.continue_construction_request(
        member_request, design_id="explicit", **selections
    ).write(root / "continued")
    return root


def test_reconcile_retains_parent_and_admits_exact_continuation(continued_family, tmp_path):
    root = continued_family
    original = (root / "saved/manifest.json").read_bytes()
    revised = construction.reconcile_construction_family(
        root / "saved", source_member="choices", outcome_path=root / "continued"
    )
    out = revised.write(tmp_path / "revised")
    assert (root / "saved/manifest.json").read_bytes() == original
    summary = json.loads(revised.json_bytes)
    assert summary["revision"]["kind"] == "continuation"
    assert summary["members"][0]["outcome"]["status"] == "complete"
    history = json.loads((out / "history/parent/summary.json").read_text())
    assert history["members"][0]["outcome"]["status"] == "selection-required"
    assert (out / "history/parent/manifest.json").read_bytes() == original
    report = construction.project_construction_family_report(out)
    assert json.loads(report.json_bytes)["members"][0]["choices"]
    assert "selection-required" in report.report_text


def test_reconciliation_rejects_foreign_request(continued_family, tmp_path):
    import shutil

    source = tmp_path / "foreign"
    shutil.copytree(continued_family / "continued", source)
    path = source / "inputs/request.json"
    data = json.loads(path.read_text())
    data["stem_arm"] = "ACGT"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="request"):
        construction.reconcile_construction_family(
            continued_family / "saved", source_member="choices", outcome_path=source
        )


def test_reconcile_cli_matches_api_and_selected_set_relocates(continued_family, tmp_path):
    import shutil

    from typer.testing import CliRunner

    from hop_design.cli import app

    root = continued_family
    out = tmp_path / "revised"
    response = CliRunner().invoke(
        app,
        [
            "construction",
            "reconcile-family",
            str(root / "saved"),
            "--source-member",
            "choices",
            "--outcome",
            str(root / "continued"),
            "--preferred-loop-nt",
            "4",
            "--out",
            str(out),
        ],
    )
    assert response.exit_code == 0, response.output
    expected = construction.reconcile_construction_family(
        root / "saved",
        source_member="choices",
        outcome_path=root / "continued",
        preferred_loop_nt=4,
    )
    assert (out / "summary.json").read_bytes() == expected.json_bytes
    request = {
        "schema": "hop.construction-set/v1",
        "baseline": "chosen",
        "members": [
            {
                "name": "chosen",
                "bundle_path": "revised/members/choices/outcome/construction",
                "selection_path": "revised/members/choices/choices/0/selection.json",
            }
        ],
        "shared_properties": [],
        "compared_properties": [],
    }
    path = tmp_path / "set.json"
    path.write_text(json.dumps(request))
    packet = construction.select_construction_set(path)
    packet.write(tmp_path / "selected")
    shutil.move(tmp_path / "selected", tmp_path / "relocated")
    assert (
        construction.select_construction_set(tmp_path / "relocated/set.json").json_bytes
        == packet.json_bytes
    )


def test_edited_alternative_keeps_original_failed_request(tmp_path):
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    data["members"] = [{"name": "short-primer", "loop_side_paired_bp": 6, "loop_nt": 3}]
    path.write_text(json.dumps(data))
    construction.execute_construction_family(path, continuation="sole-witness").write(
        tmp_path / "original"
    )
    data["members"].append({"name": "longer", "loop_side_paired_bp": 7, "loop_nt": 3})
    revised_request = tmp_path / "revised-request.json"
    revised_request.write_text(json.dumps(data))
    construction.prepare_construction_family(revised_request).write(tmp_path / "preview")
    construction.execute_construction_request(
        tmp_path / "preview/members/longer/request.json",
        design_id="explicit-edit",
        continuation="sole-witness",
    ).write(tmp_path / "alternative")
    packet = construction.reconcile_construction_family(
        tmp_path / "original",
        source_member="short-primer",
        member="longer",
        outcome_path=tmp_path / "alternative",
        revised_request=revised_request,
    )
    out = packet.write(tmp_path / "reconciled")
    result = json.loads(packet.json_bytes)
    assert result["revision"]["kind"] == "edited-request"
    assert [m["outcome"]["status"] for m in result["members"]] == ["infeasible", "complete"]
    report = construction.project_construction_family_report(
        out, baseline="longer", edits=(("short-primer", "longer"),)
    )
    assert "short-primer" in report.report_text
    assert "edited-request" in report.report_text
    with pytest.raises(ValueError, match=r"roster|retained request"):
        construction.reconcile_construction_family(
            tmp_path / "original",
            source_member="short-primer",
            outcome_path=tmp_path / "alternative",
            revised_request=revised_request,
        )


@pytest.mark.parametrize("fault", ["witness", "parent", "symlink"])
def test_reconciliation_rejects_stale_or_corrupt_authority(continued_family, tmp_path, fault):
    import shutil
    from hashlib import sha256

    source = tmp_path / "continued"
    shutil.copytree(continued_family / "continued", source)
    if fault == "symlink":
        (source / "outside").symlink_to(continued_family / "saved")
    elif fault == "witness":
        path = source / "summary.json"
        data = json.loads(path.read_text())
        data["selected_local_realizations"]["foldback"] = "foreign"
        path.write_text(json.dumps(data))
    if fault != "parent":
        with pytest.raises(ValueError):
            construction.reconcile_construction_family(
                continued_family / "saved", source_member="choices", outcome_path=source
            )
        return
    revised = construction.reconcile_construction_family(
        continued_family / "saved", source_member="choices", outcome_path=source
    ).write(tmp_path / "revised")
    summary = revised / "summary.json"
    data = json.loads(summary.read_text())
    data["revision"]["prior_status"] = "complete"
    summary.write_text(json.dumps(data))
    manifest = revised / "manifest.json"
    inventory = json.loads(manifest.read_text())
    inventory["artifacts"]["summary.json"] = "sha256:" + sha256(summary.read_bytes()).hexdigest()
    from hop_design.serialization import canonical_json_bytes

    manifest.write_bytes(canonical_json_bytes(inventory))
    with pytest.raises(ValueError, match="prior status"):
        construction.project_construction_family_report(revised)
