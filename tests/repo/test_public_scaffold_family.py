"""The shipped example lets an independent installation retrieve a comparative set."""

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_public_family_example_exports_explicit_loop_set_and_failed_member(tmp_path):
    output = tmp_path / "family"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples/complete-construction/family.py"),
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "selected/summary.json").read_text())
    assert [r["properties"]["loop_nt"] for r in summary["members"]] == [3, 4, 5]
    assert {r["properties"]["loop_side_paired_bp"] for r in summary["members"]} == {7}
    rows = list(csv.DictReader((output / "selected/oligos.csv").open()))
    assert len(rows) == 9
    outcomes = json.loads((output / "executed/summary.json").read_text())["members"]
    assert outcomes[-1]["name"] == "short-primer"
    assert outcomes[-1]["outcome"]["status"] == "infeasible"
    assert outcomes[-1]["choices"] == []


def test_public_hairpin_family_ends_at_the_requested_molecule(tmp_path):
    output = tmp_path / "hairpins"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples/complete-construction/family.py"),
            "--endpoint",
            "hairpin",
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((output / "comparison/summary.json").read_text())
    choices = [c for m in report["members"] for c in m["choices"]]
    assert len(choices) == 3
    assert {c["endpoint"] for c in choices} == {"ssdna_hairpin"}
    assert {c["stage_role"] for c in choices} == {"endpoint"}
    assert all(c["product_stages"]["product"].get("cohesive_ends", []) == [] for c in choices)
    assert (output / "authored/comparison.json").is_file()


def test_public_explicit_family_continuation(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    recipe = (
        Path(__file__).resolve().parents[2] / "examples/complete-construction/continue_family.py"
    )
    result = subprocess.run(
        [sys.executable, str(recipe), "--out", str(tmp_path / "recovery")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    original = json.loads((tmp_path / "recovery/original/summary.json").read_text())
    revised = json.loads((tmp_path / "recovery/revised/summary.json").read_text())
    assert original["members"][0]["outcome"]["status"] == "selection-required"
    assert revised["members"][0]["outcome"]["status"] == "complete"
    assert (tmp_path / "recovery/comparison/selected/oligos.csv").is_file()
