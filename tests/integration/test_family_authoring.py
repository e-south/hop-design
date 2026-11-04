"""A comparison brief exposes intent and compiles to the existing family authority."""

import json
from pathlib import Path

import pytest

from hop_design import construction
from tests.integration.test_request_execution import request_path


def brief_path(root: Path):
    base = request_path(root)
    brief = {
        "schema": "hop.scaffold-comparison/v1",
        "base_request": base.name,
        "product": "clone_ready_duplex",
        "vary": [
            {"name": "loop3", "loop_nt": 3, "loop_side_paired_bp": 7},
            {"name": "loop4", "loop_nt": 4, "loop_side_paired_bp": 7},
        ],
        "hold": ["stem_sequence", "endpoint", "release_interfaces"],
        "geometry_permissions": {"loop_nt": [3, 4], "loop_side_paired_bp": [7]},
        "bounds": {"max_members": 2, "max_total_search_nodes": 40000, "max_total_continuations": 2},
    }
    path = root / "comparison.json"
    path.write_text(json.dumps(brief))
    return path


def test_brief_authors_exact_family_and_explains_material_permissions(tmp_path):
    path = brief_path(tmp_path)
    base = (tmp_path / json.loads(path.read_text())["base_request"]).read_bytes()
    packet = construction.author_construction_family(path)
    summary = json.loads(packet.json_bytes)
    assert summary["executable"] is True
    assert summary["comparison_intent"]["endpoint"] == "clone_ready_duplex"
    assert (
        summary["comparison_intent"]["materials"]["source_preparation"]["reverse_primer"]["mode"]
        == "derive"
    )
    assert "released duplex insert" in packet.report_text
    assert "loop3: loop 3 nt; loop-side extension 7 bp" in packet.report_text
    assert "Material changes permitted" in packet.report_text
    output = packet.write(tmp_path / "authored")
    canonical = json.loads((output / "family.json").read_text())
    assert canonical["base_request"]["foldback"]["geometry"]["loop_lengths_nt"] == [3, 4]
    assert (tmp_path / json.loads(path.read_text())["base_request"]).read_bytes() == base
    assert (
        construction.prepare_construction_family(output / "family.json").json_bytes
        == packet.json_bytes
    )


def test_brief_does_not_remove_conflicting_requirements(tmp_path):
    path = brief_path(tmp_path)
    b = tmp_path / json.loads(path.read_text())["base_request"]
    data = json.loads(b.read_text())
    data["whole_route_constraints"]["hairpin_scaffold"] = {"loop_nt": {"minimum": 4, "maximum": 4}}
    b.write_text(json.dumps(data))
    summary = json.loads(construction.author_construction_family(path).json_bytes)
    assert summary["executable"] is False
    assert "hard requirement" in summary["members"][0]["conflict"]


@pytest.mark.parametrize("fault", ["unsupported", "endpoint", "unknown", "bounds"])
def test_brief_rejects_unavailable_or_undeclared_controls(tmp_path, fault):
    path = brief_path(tmp_path)
    data = json.loads(path.read_text())
    if fault == "unsupported":
        data["vary"][0]["open_side_paired_positions"] = 20
    elif fault == "endpoint":
        data["product"] = "ssdna_hairpin"
    elif fault == "unknown":
        data["invented"] = 1
    else:
        data["bounds"]["max_members"] = 1
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        construction.author_construction_family(path)


def test_author_cli_matches_api_and_explicit_requirement_replacement(tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app

    path = brief_path(tmp_path)
    brief = json.loads(path.read_text())
    base = tmp_path / brief["base_request"]
    data = json.loads(base.read_text())
    data["whole_route_constraints"]["hairpin_scaffold"] = {"loop_nt": {"minimum": 4, "maximum": 4}}
    base.write_text(json.dumps(data))
    brief["requirements"] = None
    path.write_text(json.dumps(brief))
    expected = construction.author_construction_family(path)
    assert json.loads(expected.json_bytes)["executable"] is True
    result = CliRunner().invoke(
        app, ["construction", "author-family", str(path), "--out", str(tmp_path / "cli")]
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "cli/summary.json").read_bytes() == expected.json_bytes
