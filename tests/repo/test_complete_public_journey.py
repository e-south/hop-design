"""Exercise the public preparation example through installed HOP interfaces."""

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "complete-construction"


def test_public_journey_reports_the_authored_stem_length(tmp_path):
    example = tmp_path / "example"
    shutil.copytree(EXAMPLE, example)
    request_path = example / "product-request.json"
    request = json.loads(request_path.read_text())
    request["stem_arm"] = request["stem_arm"][:20]
    request_path.write_text(json.dumps(request))
    output = tmp_path / "journey"
    result = subprocess.run(
        [sys.executable, str(example / "run.py"), "--out", str(output)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "summary.json").read_text())
    source = json.loads((output / "released" / "inputs" / "construction.json").read_text())
    payload = source["foldback"]["payload"]["payload"]["sequence"]
    assert payload == request["stem_arm"]
    assert summary["payload_nt"] == len(payload) == 20


def test_public_journey_replays_products_and_fixed_source_rejection(tmp_path):
    output = tmp_path / "journey"
    result = subprocess.run(
        [sys.executable, str(EXAMPLE / "run.py"), "--out", str(output)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "summary.json").read_text())
    assert summary["payload_nt"] == 34
    assert {case: row["status"] for case, row in summary["cases"].items()} == {
        "released": "complete",
        "hairpin": "complete",
        "fixed-source-edit": "infeasible",
        "redesigned-source-edit": "complete",
    }
    materials_by_case = {}
    for case, words in (
        ("released", {"left": "AGTC", "right": "AGTC"}),
        ("redesigned-source-edit", {"left": "GATC", "right": "AGTC"}),
    ):
        row = summary["cases"][case]
        assert row["actual_ends"] == words
        projection = json.loads((output / case / "handoff" / "projection.json").read_text())
        assert projection["source_result_id"] == row["result_id"]
        assert {
            end["product_end"]: end["sequence"]
            for end in projection["realization"]["final_product"]["cohesive_ends"]
        } == words
        with (output / case / "handoff" / "oligos.csv").open() as handle:
            oligos = list(csv.DictReader(handle))
        assert len(oligos) >= 5
        assert {oligo["five_prime_end"] for oligo in oligos} == {"hydroxyl", "phosphate"}
        materials_by_case[case] = {
            role: (oligo["sequence_5prime"], oligo["five_prime_end"], oligo["three_prime_end"])
            for oligo in oligos
            for role in oligo["roles"].split(";")
        }
    reference = materials_by_case["released"]
    alternative = materials_by_case["redesigned-source-edit"]
    assert reference.keys() == alternative.keys()
    assert {role for role in reference if reference[role] != alternative[role]} == {"source_ssdna"}
    failed = summary["cases"]["fixed-source-edit"]
    assert failed["rejection_reasons"] == ["source-preparation-incompatible"]
    assert failed["accepted"] == 0
    assert not (output / "fixed-source-edit" / "handoff").exists()
    assert summary["cases"]["hairpin"]["actual_ends"] == {}
    assert summary["producer"]["package_content"].startswith("sha256:")


def test_tutorial_can_start_at_hairpin_without_an_insert_run(tmp_path):
    output = tmp_path / "hairpin-only"
    result = subprocess.run(
        [sys.executable, str(EXAMPLE / "run.py"), "--case", "hairpin", "--out", str(output)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "summary.json").read_text())
    assert list(summary["cases"]) == ["hairpin"]
    assert summary["cases"]["hairpin"]["status"] == "complete"
    assert not (output / "released").exists()
    portrait = json.loads((output / "hairpin/portrait/projection.json").read_text())
    assert portrait["stem_bp"] == 34
    assert portrait["stage_role"] == "endpoint"
    assert (output / "hairpin/portrait/preparation/oligos.csv").read_bytes() == (
        output / "hairpin/handoff/oligos.csv"
    ).read_bytes()


def test_tutorial_end_edit_retains_expected_failure_without_traceback(tmp_path):
    example = tmp_path / "example"
    shutil.copytree(EXAMPLE, example)
    path = example / "product-request.json"
    authored = json.loads(path.read_text())
    authored["ends"]["left"]["cohesive_end_sequence"] = "GATC"
    path.write_text(json.dumps(authored))
    output = tmp_path / "edited"
    result = subprocess.run(
        [sys.executable, str(example / "run.py"), "--out", str(output)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "summary.json").read_text())
    assert summary["cases"]["released"]["status"] == "infeasible"
    assert summary["cases"]["released"]["stage"] == "basal"
    assert (output / "released/report.md").is_file()
    assert (output / "manifest.json").is_file()
    assert "Traceback" not in result.stderr
