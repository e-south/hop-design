"""A bounded request must return an inspectable preparation or scoped absence."""

import csv
import json
from importlib.metadata import version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app

ROOT = Path(__file__).resolve().parents[2]


def request_path(tmp_path, *, left="AGTC"):
    request = json.loads((ROOT / "examples/complete-construction/product-request.json").read_text())
    request["ends"]["left"]["cohesive_end_sequence"] = left
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    return path


def test_failed_request_keeps_requested_ends_and_recorded_local_causes_visible(tmp_path):
    path = request_path(tmp_path, left="CATT")
    authored = json.loads(path.read_text())
    geometry = authored["basal"]["geometry"]
    geometry["max_noncanonical_pairs"] = 4
    for contact in geometry["pairing_constraints"]:
        if 6 <= contact["position_from_ligation"] < 10:
            contact["allowed_class"] = "any"
    path.write_text(json.dumps(authored))
    receipt = construction.execute_construction_request(
        path, design_id="visible-local-cause", continuation="sole-witness"
    )
    receipt.write(tmp_path / "outcome")
    summary = json.loads(receipt.json_bytes)
    assert summary["status"] == "infeasible"
    assert summary["rejection_reasons"] == ["unintended-actionable-site"]
    assert summary["requested_ends"] == authored["ends"]
    assert summary["local_coverage"]["basal"]["rejection_counts"] == {
        "unintended-actionable-site": 4
    }
    for expected in (
        "CATT",
        "AGTC",
        "6 bp",
        "released duplex insert",
        "unintended-actionable-site: 4",
    ):
        assert expected in receipt.report_text
    assert "site orientation: forward" in receipt.report_text
    assert "site orientation: reverse" in receipt.report_text
    assert "forward strand" not in receipt.report_text
    assert "not a uniquely necessary repair" in receipt.report_text
    assert "Downstream construction was not evaluated" in receipt.report_text
    local = json.loads((tmp_path / "outcome/basal/result.json").read_text())["discovery"]
    assert local["failure_reasons"] == [{"code": "unintended-actionable-site", "count": 4}]


@pytest.mark.parametrize("left", ["AGTC", "GATC"])
def test_invalid_design_identity_is_rejected_before_discovery(tmp_path, monkeypatch, left):
    from hop_design.design.construction import request_execution

    path = request_path(tmp_path, left=left)

    def unexpected_discovery(*args, **kwargs):
        raise AssertionError("Malformed identity must not start molecular discovery")

    monkeypatch.setattr(request_execution, "discover_local_neighborhood", unexpected_discovery)
    with pytest.raises(ValueError, match="design_id"):
        construction.execute_construction_request(
            path, design_id="invalid-UPPERCASE", continuation="sole-witness"
        )


def test_execute_request_returns_verified_preparation_with_cli_api_parity(tmp_path):
    path = request_path(tmp_path)
    receipt = construction.execute_construction_request(
        path, design_id="request-test", continuation="sole-witness"
    )
    receipt.write(tmp_path / "api")
    summary = json.loads(receipt.json_bytes)
    assert summary["status"] == "complete"
    assert summary["stage"] == "construction"
    assert summary["accepted"] == 1
    assert summary["producer"]["package_version"] == version("hop-design")
    assert summary["producer"]["package_content"].startswith("sha256:")
    assert summary["continuation"] == "sole-witness"
    assert summary["local_coverage"]["basal"]["completion"] == "stopped_by_policy"
    verified = construction.load_verified_construction_bundle(tmp_path / "api/construction")
    assert summary["result_id"] == verified.result_id
    assert (tmp_path / "api/handoff/oligos.csv").is_file()
    report = (tmp_path / "api/handoff/report.md").read_text()
    assert "BsaI-HFv2" in report
    assert "Nt.Bpu10I" in report
    assert "example:enzyme/bsai-hfv2@1" in report
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "execute",
            str(path),
            "--design-id",
            "request-test",
            "--continuation",
            "sole-witness",
            "--out",
            str(tmp_path / "cli"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "cli/summary.json").read_bytes() == receipt.json_bytes
    assert (tmp_path / "cli/handoff/oligos.csv").read_bytes() == (
        tmp_path / "api/handoff/oligos.csv"
    ).read_bytes()


@pytest.mark.parametrize("stop", ["exhausted", "bounded", "multiple"])
def test_local_absence_or_ambiguity_is_a_scoped_handoff(tmp_path, stop):
    path = request_path(tmp_path, left="GATC" if stop == "exhausted" else "AGTC")
    authored = json.loads(path.read_text())
    if stop == "bounded":
        # An internal nicking site rejects the first candidate; the bound leaves
        # later geometry unexamined, so this cannot establish global absence.
        authored["stem_arm"] = "CCTGAGC"
        authored["foldback"]["geometry"]["loop_lengths_nt"] = [3, 4, 5]
        authored["foldback"]["search"]["max_search_nodes"] = 1
    elif stop == "multiple":
        authored["foldback"]["geometry"]["loop_lengths_nt"] = [4, 5]
        authored["foldback"]["search"].update(
            max_realizations=2, result_quota=2, max_retained_overhead_nt=20
        )
    path.write_text(json.dumps(authored))
    receipt = construction.execute_construction_request(
        path, design_id="negative-test", continuation="sole-witness"
    )
    receipt.write(tmp_path / "outcome")
    summary = json.loads(receipt.json_bytes)
    family = "basal" if stop == "exhausted" else "foldback"
    assert summary["stage"] == family
    assert summary["scope"] == "local_domain"
    assert (
        summary["status"]
        == {"exhausted": "infeasible", "bounded": "unresolved", "multiple": "selection-required"}[
            stop
        ]
    )
    assert summary["accepted"] == 0
    assert summary["result_id"] is None
    assert (tmp_path / "outcome" / family / "result.json").is_file()
    assert not (tmp_path / "outcome/construction").exists()
    assert not (tmp_path / "outcome/handoff").exists()
    assert "not a uniquely necessary repair" in receipt.report_text
    assert json.loads((tmp_path / "outcome/inputs/request.json").read_text()) == authored
    if stop == "exhausted":
        assert summary["local_coverage"][family]["completion"] == "complete"
        result = CliRunner().invoke(
            app,
            [
                "construction",
                "execute",
                str(path),
                "--design-id",
                "negative-test",
                "--continuation",
                "sole-witness",
                "--out",
                str(tmp_path / "cli"),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Traceback" not in result.output
        assert (tmp_path / "cli/summary.json").read_bytes() == receipt.json_bytes


def hairpin_request(tmp_path):
    path = request_path(tmp_path)
    authored = json.loads(path.read_text())
    authored.update(endpoint="ssdna_hairpin", ends=None, basal=None, release=None)
    authored["hairpin_basal_component"] = {"left_arm": "AGTCGCAATG", "right_arm": "CATTGCGACT"}
    authored["enzyme_catalog"]["enzymes"] = [
        e
        for e in authored["enzyme_catalog"]["enzymes"]
        if e["enzyme_id"] in authored["foldback"]["enzymes"]["allowed_enzyme_ids"]
    ]
    materialization = authored["materialization"]
    materialization.pop("endpoint_auxiliaries")
    materialization["source_preparation"]["source_ssdna"] = {
        "mode": "derive",
        "five_prime_end": "hydroxyl",
        "three_prime_end": "hydroxyl",
    }
    materialization["source_preparation"]["forward_primer"]["annealing_length_nt"] = 10
    path.write_text(json.dumps(authored))
    return path


def test_hairpin_request_needs_no_insert_authority_or_downstream_enzymes(tmp_path):
    path = hairpin_request(tmp_path)
    receipt = construction.execute_construction_request(
        path, design_id="standalone-hairpin", continuation="sole-witness"
    )
    receipt.write(tmp_path / "hairpin")
    summary = json.loads(receipt.json_bytes)
    assert summary["status"] == "complete"
    assert summary["endpoint"] == "ssdna_hairpin"
    assert set(summary["local_coverage"]) == {"foldback"}
    projection = json.loads((tmp_path / "hairpin/handoff/projection.json").read_text())
    route = projection["realization"]
    assert route["basal_authority"] is None
    assert [len(s["sequence"]) for s in route["final_product"]["strands"]] == [104]
    assert len(route["source_preparation"]["source_ssdna"]["sequence_5prime"]) == 58
    with (tmp_path / "hairpin/handoff/oligos.csv").open() as handle:
        assert len(list(csv.DictReader(handle))) == 3


def test_hairpin_without_a_component_rejects_before_publication(tmp_path):
    path = hairpin_request(tmp_path)
    authored = json.loads(path.read_text())
    authored.pop("hairpin_basal_component")
    path.write_text(json.dumps(authored))
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "execute",
            str(path),
            "--design-id",
            "missing-component",
            "--continuation",
            "sole-witness",
            "--out",
            str(tmp_path / "missing"),
        ],
    )
    assert result.exit_code == 2
    assert "hairpin_basal_component" in result.output
    assert not (tmp_path / "missing").exists()


def test_fixed_source_rejection_preserves_a_complete_failure_handoff(tmp_path):
    path = request_path(tmp_path)
    construction.execute_construction_request(
        path, design_id="reference", continuation="sole-witness"
    ).write(tmp_path / "reference")
    reference = json.loads((tmp_path / "reference/handoff/projection.json").read_text())
    authored = json.loads(path.read_text())
    authored["ends"]["left"]["cohesive_end_sequence"] = "GATC"
    geometry = authored["basal"]["geometry"]
    geometry["max_noncanonical_pairs"] = 4
    for contact in geometry["pairing_constraints"]:
        if 6 <= contact["position_from_ligation"] < 10:
            contact["allowed_class"] = "any"
    authored["materialization"]["source_preparation"]["source_ssdna"] = {
        "mode": "fixed",
        "material": reference["realization"]["source_preparation"]["source_ssdna"],
    }
    path.write_text(json.dumps(authored))
    receipt = construction.execute_construction_request(
        path, design_id="fixed-edit", continuation="sole-witness"
    )
    receipt.write(tmp_path / "rejected")
    summary = json.loads(receipt.json_bytes)
    assert summary["stage"] == "construction"
    assert summary["status"] == "infeasible"
    assert summary["scope"] == "selected_combination"
    assert summary["rejection_reasons"] == ["source-preparation-incompatible"]
    assert "source-preparation-incompatible" in receipt.report_text
    assert "not a uniquely necessary repair" in receipt.report_text
    assert not (tmp_path / "rejected/handoff").exists()
    assert (
        construction.load_verified_construction_bundle(tmp_path / "rejected/construction").status
        == "infeasible"
    )
    with pytest.raises(FileExistsError):
        receipt.write(tmp_path / "rejected")


@pytest.mark.parametrize(
    "invalid", ["unequal-arms", "symbolic-arm", "wrong-endpoint", "unknown-field"]
)
def test_malformed_components_never_publish_an_outcome(tmp_path, invalid):
    path = hairpin_request(tmp_path)
    authored = json.loads(path.read_text())
    if invalid == "unequal-arms":
        authored["hairpin_basal_component"]["right_arm"] = "A"
    elif invalid == "symbolic-arm":
        authored["hairpin_basal_component"]["left_arm"] = "N" * 10
    elif invalid == "wrong-endpoint":
        path = request_path(tmp_path)
        authored = json.loads(path.read_text())
        authored["hairpin_basal_component"] = {"left_arm": "A", "right_arm": "T"}
    else:
        authored["hairpin_basal_component"]["invented"] = True
    path.write_text(json.dumps(authored))
    with pytest.raises(ValueError):
        construction.execute_construction_request(
            path, design_id="invalid", continuation="sole-witness"
        )
