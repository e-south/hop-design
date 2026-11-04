"""A bounded family preserves named intent, effective domains and every outcome."""

import json
from hashlib import sha256

import pytest

from hop_design import construction
from tests.integration.test_request_execution import request_path


def family_path(tmp_path):
    base = json.loads(request_path(tmp_path).read_text())
    base["foldback"]["geometry"]["annealing_arm_lengths_bp"] = [6, 7]
    base["foldback"]["geometry"]["loop_lengths_nt"] = [3, 4, 5]
    base["foldback"]["search"]["max_retained_overhead_nt"] = 21
    data = {
        "schema": "hop.construction-family/v1",
        "base_request": base,
        "members": [
            {"name": "loop3", "loop_side_paired_bp": 7, "loop_nt": 3},
            {"name": "loop4", "loop_side_paired_bp": 7, "loop_nt": 4},
            {"name": "short-primer", "loop_side_paired_bp": 6, "loop_nt": 3},
        ],
        "shared_properties": [
            "stem_sequence",
            "endpoint",
            "release_interfaces",
            "open_side_paired_positions",
        ],
        "display_preferences": [{"dimension": "loop_nt", "direction": "ascending"}],
        "bounds": {"max_members": 3, "max_total_search_nodes": 60000, "max_total_continuations": 3},
    }
    path = tmp_path / "family.json"
    path.write_text(json.dumps(data))
    return path


def test_family_preview_narrows_declared_domains_without_search(tmp_path, monkeypatch):
    from hop_design.design.construction import request_execution

    def forbidden(*args, **kwargs):
        raise AssertionError("Preview must not search")

    monkeypatch.setattr(request_execution, "discover_local_neighborhood", forbidden)
    path = family_path(tmp_path)
    prepared = construction.prepare_construction_family(path)
    preview = json.loads(prepared.json_bytes)
    assert preview["executable"] is True
    assert preview["upper_bounds"]["search_nodes"] == 60000
    assert [m["name"] for m in preview["members"]] == ["loop3", "loop4", "short-primer"]
    prepared.write(tmp_path / "preview")
    member = json.loads((tmp_path / "preview/members/loop3/request.json").read_text())
    assert member["foldback"]["geometry"]["loop_lengths_nt"] == [3]
    assert member["foldback"]["geometry"]["annealing_arm_lengths_bp"] == [7]
    original = json.loads(path.read_text())["base_request"]
    assert member["materialization"] == original["materialization"]
    assert member["ends"] == original["ends"]


def test_family_preview_explains_domain_conflict_and_execution_refuses_it(tmp_path, monkeypatch):
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    data["base_request"]["foldback"]["geometry"]["loop_lengths_nt"] = [4]
    path.write_text(json.dumps(data))
    preview = json.loads(construction.prepare_construction_family(path).json_bytes)
    assert preview["executable"] is False
    assert "loop_lengths_nt" in preview["members"][0]["conflict"]
    with pytest.raises(ValueError, match="conflict"):
        construction.execute_construction_family(path, continuation="sole-witness")


@pytest.mark.parametrize("fault", ["budget", "duplicate", "shared-varied", "unknown"])
def test_family_rejects_unbounded_or_ambiguous_intent_before_execution(tmp_path, fault):
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    if fault == "budget":
        data["bounds"]["max_total_search_nodes"] = 59999
    elif fault == "duplicate":
        data["members"][1]["name"] = "loop3"
    elif fault == "shared-varied":
        data["shared_properties"].append("loop_nt")
    else:
        data["members"][0]["new_topology"] = "sticky-hairpin"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        construction.prepare_construction_family(path)


def test_family_execution_preserves_a_failed_preparation_beside_complete_choices(tmp_path):
    path = family_path(tmp_path)
    packet = construction.execute_construction_family(path, continuation="sole-witness")
    summary = json.loads(packet.json_bytes)
    assert summary["schema"] == "hop.construction-family-result/v1"
    assert summary["display_order"] == ["loop3", "loop4"]
    members = {m["name"]: m for m in summary["members"]}
    assert [members[n]["outcome"]["status"] for n in ("loop3", "loop4", "short-primer")] == [
        "complete",
        "complete",
        "infeasible",
    ]
    assert members["short-primer"]["outcome"]["scope"] == "selected_combination"
    assert members["short-primer"]["choices"] == []
    assert members["loop3"]["choices"][0]["geometry"]["loop_nt"] == 3
    packet.write(tmp_path / "family-result")
    assert (
        tmp_path / "family-result/members/loop3/outcome/construction/construction-bundle.json"
    ).is_file()
    assert (tmp_path / "family-result/members/short-primer/outcome/summary.json").is_file()
    assert not (tmp_path / "family-result/members/short-primer/portrait").exists()
    manifest = json.loads((tmp_path / "family-result/manifest.json").read_text())
    assert "manifest.json" not in manifest["artifacts"]
    for name, digest in manifest["artifacts"].items():
        assert (
            digest
            == "sha256:" + sha256((tmp_path / "family-result" / name).read_bytes()).hexdigest()
        )


def test_family_cli_uses_the_same_preview_and_execution_packets(tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app

    path = family_path(tmp_path)
    for command, api in (
        ("prepare-family", construction.prepare_construction_family),
        ("execute-family", construction.execute_construction_family),
    ):
        arguments = ["construction", command, str(path), "--out", str(tmp_path / command)]
        kwargs = {}
        if command == "execute-family":
            arguments += ["--continuation", "sole-witness"]
            kwargs["continuation"] = "sole-witness"
        result = CliRunner().invoke(app, arguments)
        assert result.exit_code == 0, result.output
        assert (tmp_path / command / "summary.json").read_bytes() == api(path, **kwargs).json_bytes


def test_family_retains_stopped_searches_without_fabricating_choices(tmp_path):
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    data["members"] = data["members"][:2]
    for member in data["members"]:
        member.pop("loop_side_paired_bp")
    data["base_request"]["stem_arm"] = "CCTGAGC"
    data["base_request"]["foldback"]["search"]["max_search_nodes"] = 1
    path.write_text(json.dumps(data))
    summary = json.loads(
        construction.execute_construction_family(path, continuation="sole-witness").json_bytes
    )
    assert len(summary["members"]) == 2
    assert all(m["outcome"]["status"] == "unresolved" for m in summary["members"])
    assert all(m["outcome"]["scope"] == "local_domain" for m in summary["members"])
    assert summary["display_choices"] == []


def test_family_does_not_select_between_multiple_local_witnesses(tmp_path):
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    data["members"] = [{"name": "extension7", "loop_side_paired_bp": 7}]
    data["base_request"]["foldback"]["search"].update(max_realizations=2, result_quota=2)
    path.write_text(json.dumps(data))
    summary = json.loads(
        construction.execute_construction_family(path, continuation="sole-witness").json_bytes
    )
    member = summary["members"][0]
    assert member["outcome"]["status"] == "selection-required"
    assert member["outcome"]["local_coverage"]["foldback"]["realization_count"] == 2
    assert member["choices"] == []
    assert summary["display_choices"] == []


def test_family_preserves_source_chemistry_without_changing_scaffold(tmp_path):
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    data["members"] = data["members"][:1]
    data["base_request"]["materialization"]["source_preparation"]["source_ssdna"][
        "five_prime_end"
    ] = "phosphate"
    path.write_text(json.dumps(data))
    packet = construction.execute_construction_family(path, continuation="sole-witness")
    member = json.loads(packet.json_bytes)["members"][0]
    assert member["outcome"]["status"] == "complete"
    choice = member["choices"][0]
    assert choice["geometry"]["loop_nt"] == 3
    assert choice["geometry"]["loop_side_paired_bp"] == 7
    assert choice["eligible_for_shared_family"] is True
    packet.write(tmp_path / "phosphorylated")
    import csv

    oligos = list(
        csv.DictReader(
            (tmp_path / "phosphorylated/members/loop3/choices/0/preparation/oligos.csv").open()
        )
    )
    source = next(r for r in oligos if r["name"] == "source_ssdna")
    assert source["five_prime_end"] == "phosphate"


def test_shared_dimension_may_be_inherited_from_the_base_domain(tmp_path):
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    data["base_request"]["foldback"]["geometry"]["loop_lengths_nt"] = [3]
    data["base_request"]["foldback"]["geometry"]["annealing_arm_lengths_bp"] = [7, 8]
    data["members"] = [
        {"name": "shorter", "loop_side_paired_bp": 7, "loop_nt": 3},
        {"name": "longer", "loop_side_paired_bp": 8},
    ]
    data["shared_properties"].append("loop_nt")
    path.write_text(json.dumps(data))
    preview = json.loads(construction.prepare_construction_family(path).json_bytes)
    assert preview["executable"] is True
    assert all(m["effective_geometry"]["loop_lengths_nt"] == [3] for m in preview["members"])
