"""A public family report preserves user intent, all outcomes and exact selections."""

import json
import shutil
from pathlib import Path

import pytest

from hop_design import construction
from tests.integration.test_construction_family import family_path


@pytest.fixture(scope="module")
def family_capture(tmp_path_factory):
    root = tmp_path_factory.mktemp("family-report-inputs")
    request = family_path(root)
    family = construction.execute_construction_family(request, continuation="sole-witness")
    family.write(root / "executed")
    data = json.loads(family.json_bytes)
    membership = {
        "schema": "hop.construction-set/v1",
        "baseline": "loop3",
        "shared_properties": [*data["shared_properties"], "loop_side_paired_bp"],
        "compared_properties": ["loop_nt"],
        "members": [
            {
                "name": member["name"],
                "bundle_path": f"executed/members/{member['name']}/outcome/construction",
                "selection_path": "executed/" + member["choices"][0]["selection"],
            }
            for member in data["members"]
            if member["choices"]
        ],
    }
    (root / "set.json").write_text(json.dumps(membership))
    return root


def test_report_retains_requests_failure_and_explicit_selection_without_new_execution(
    family_capture, tmp_path, monkeypatch
):
    from hop_design.design.construction import request_execution
    from hop_design.design.construction.families import execute

    def forbidden(*args, **kwargs):
        raise AssertionError("Reporting must not launch new request execution or discovery")

    monkeypatch.setattr(execute, "execute_construction_request", forbidden)
    monkeypatch.setattr(request_execution, "discover_local_neighborhood", forbidden)
    report = construction.project_construction_family_report(
        family_capture / "executed", selection=family_capture / "set.json", baseline="loop3"
    )
    summary = json.loads(report.json_bytes)
    assert summary["schema"] == "hop.construction-family-report/v3"
    assert [m["name"] for m in summary["members"]] == ["loop3", "loop4", "short-primer"]
    members = {m["name"]: m for m in summary["members"]}
    assert members["loop3"]["requested_variation"]["loop_nt"] == 3
    assert members["loop3"]["choices"][0]["geometry"]["loop_nt"] == 3
    assert members["short-primer"]["status"] == "infeasible"
    assert members["short-primer"]["scope"] == "selected_combination"
    assert members["short-primer"]["choices"] == []
    diagnostic = members["short-primer"]["preparation_constraints"][0]
    assert diagnostic["requested"] == 14
    assert diagnostic["available"] == 13
    assert summary["selected_members"] == ["loop3", "loop4"]
    output = report.write(tmp_path / "report")
    assert (output / "report.svg").is_file()
    assert "short-primer" in report.report_text
    for member in members.values():
        for choice in member["choices"]:
            assert (output / choice["preparation"]).is_file()
            assert not Path(choice["preparation"]).is_absolute()


def test_report_does_not_select_a_family_by_display_order(family_capture):
    report = construction.project_construction_family_report(family_capture / "executed")
    assert json.loads(report.json_bytes)["selected_members"] == []


def reseal(root):
    from hop_design.serialization import canonical_json_bytes, sha256_digest

    manifest = json.loads((root / "manifest.json").read_text())
    manifest["artifacts"] = {
        p.relative_to(root).as_posix(): sha256_digest(p.read_bytes())
        for p in root.rglob("*")
        if p.is_file() and p != root / "manifest.json"
    }
    (root / "manifest.json").write_bytes(canonical_json_bytes(manifest))


@pytest.mark.parametrize("fault", ["choice", "outcome", "request", "producer", "shared-reference"])
def test_report_rejects_checksum_consistent_family_forgery(family_capture, tmp_path, fault):
    copied = tmp_path / "forged"
    shutil.copytree(family_capture / "executed", copied)
    summary_path = copied / "summary.json"
    data = json.loads(summary_path.read_text())
    if fault == "choice":
        data["members"][0]["choices"][0]["geometry"]["loop_nt"] = 999
    elif fault == "outcome":
        data["members"][-1]["outcome"]["status"] = "complete"
    elif fault == "request":
        p = copied / "family.json"
        changed = json.loads(p.read_text())
        changed["base_request"]["stem_arm"] = "ACGT"
        p.write_text(json.dumps(changed))
    elif fault == "producer":
        data["members"][0]["outcome"]["producer"]["version"] = "invented"
    else:
        data["shared_reference"]["properties"]["loop_nt"] = 999
    summary_path.write_text(json.dumps(data))
    reseal(copied)
    with pytest.raises(ValueError):
        construction.project_construction_family_report(copied)


def test_cli_report_matches_api_and_remains_portable(family_capture, tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app

    output = tmp_path / "report"
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "report-family",
            str(family_capture / "executed"),
            "--selection",
            str(family_capture / "set.json"),
            "--baseline",
            "loop3",
            "--out",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    expected = construction.project_construction_family_report(
        family_capture / "executed", selection=family_capture / "set.json", baseline="loop3"
    )
    assert (output / "summary.json").read_bytes() == expected.json_bytes
    assert (output / "report.pdf").read_bytes().startswith(b"%PDF-")
    other = expected.write(tmp_path / "api")
    assert (output / "report.pdf").read_bytes() == (other / "report.pdf").read_bytes()
    moved = tmp_path / "moved"
    output.rename(moved)
    selected = construction.select_construction_set(moved / "selected/set.json")
    assert json.loads(selected.json_bytes)["members"][0]["name"] == "loop3"


def test_report_exposes_actual_loop_change_and_its_material_consequences(family_capture):
    packet = construction.project_construction_family_report(
        family_capture / "executed", baseline="loop3"
    )
    comparison = json.loads(packet.json_bytes)["comparisons"][0]
    assert comparison["member"] == "loop4"
    loop = next(r for r in comparison["regions"] if r["region"] == "loop")
    assert (loop["reference_sequence"], loop["observed_sequence"]) == ("AAA", "AAAA")
    assert loop["correspondence"] == "ambiguous_minimum_edit"
    assert set(comparison["molecular"]["changed_material_roles"]) == {
        "source_ssdna",
        "source_materialization_reverse_primer",
    }


def test_report_matches_intermediate_to_its_actual_released_product(family_capture, tmp_path):
    packet = construction.project_construction_family_report(family_capture / "executed")
    choice = json.loads(packet.json_bytes)["members"][0]["choices"][0]
    stages = choice["product_stages"]
    assert stages["hairpin_role"] == "intermediate"
    assert stages["endpoint"] == "clone_ready_duplex"
    assert stages["product"]["strands"][0]["sequence"] == "".join(
        b["base"] for b in stages["bases"] if b["strand_index"] == 0
    )
    assert [e["sequence"] for e in stages["product"]["cohesive_ends"]] == ["AGTC", "AGTC"]
    assert {b["region"] for b in stages["bases"]} == {"open", "stem", "closing"}
    output = packet.write(tmp_path / "stages")
    assert b"clone_ready_duplex" in (output / choice["stage_drawing"]).read_bytes()


def test_report_draws_countable_loops_and_explains_ambiguous_changes(family_capture, tmp_path):
    from xml.etree import ElementTree as ET

    packet = construction.project_construction_family_report(
        family_capture / "executed", baseline="loop3"
    )
    output = packet.write(tmp_path / "readable")
    summary = json.loads(packet.json_bytes)
    for member in summary["members"]:
        for choice in member["choices"]:
            root = ET.parse(output / choice["closing_drawing"]).getroot()
            labels = [e for e in root.iter() if e.get("data-loop-index") is not None]
            assert len(labels) == choice["geometry"]["loop_nt"]
            assert all(e.text == "A" for e in labels)
    overview = ET.parse(output / "report.svg").getroot()
    text = " ".join(overview.itertext())
    assert "Requested" in text and "Obtained" in text
    assert "selected preparation" in text
    assert "ambiguous" in packet.report_text.lower()


def test_report_records_authored_alternative_without_implying_repair(family_capture):
    packet = construction.project_construction_family_report(
        family_capture / "executed", edits=(("short-primer", "loop3"),)
    )
    edit = json.loads(packet.json_bytes)["authored_edits"][0]
    assert edit["source_member"] == "short-primer"
    assert edit["target_member"] == "loop3"
    assert edit["requested_changes"]["loop_side_paired_bp"] == [6, 7]
    assert json.loads(packet.json_bytes)["selected_members"] == []
    assert "not a uniquely necessary repair" in packet.report_text
    with pytest.raises(ValueError, match="member"):
        construction.project_construction_family_report(
            family_capture / "executed", edits=(("missing", "loop3"),)
        )
