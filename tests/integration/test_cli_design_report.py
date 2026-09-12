from __future__ import annotations

import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

from hop_design import compile as compile_design
from hop_design.cli import app

runner = CliRunner()


def test_compile_report_matches_verified_bundle_without_changing_bundle_bytes(
    tmp_path: Path,
) -> None:
    target = tmp_path / "bundle"
    result = runner.invoke(app, ["compile", "--sequence", "ACGT", "--out", str(target), "--report"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["schema"] == "hop/design-report/v1"
    assert report["verification"] == "deterministic_derivation"
    assert report["plan"] == json.loads((target / "hop-plan.json").read_bytes())
    assert report["bundle"] == json.loads((target / "hop-bundle.json").read_bytes())
    assert (
        report["bundle_file_sha256"]
        == "sha256:" + hashlib.sha256((target / "hop-bundle.json").read_bytes()).hexdigest()
    )
    expected = compile_design(sequence="ACGT")
    assert {path.name for path in target.iterdir()} == set(expected.artifacts) | {"hop-bundle.json"}
    verified = runner.invoke(app, ["verify", str(target), "--report"])
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output) == report


def test_dry_run_report_needs_no_publication(tmp_path: Path) -> None:
    result = runner.invoke(app, ["compile", "--sequence", "ACGT", "--dry-run", "--report"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["plan"]["hairpin_encoding_insert"]["sequence"]
    assert report["spec"]["payload"]["sequence"] == "ACGT"
    assert list(tmp_path.iterdir()) == []


def test_verify_report_rejects_corrupt_bundle(tmp_path: Path) -> None:
    target = compile_design(sequence="ACGT").write(tmp_path / "bundle")
    (target / "hop-plan.json").write_bytes(b"{}\n")

    result = runner.invoke(app, ["verify", str(target), "--report"])

    assert result.exit_code != 0
    assert '"verification"' not in result.output
