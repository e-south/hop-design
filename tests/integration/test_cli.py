from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from hop_design.api import create_spec, verify_bundle
from hop_design.cli import app
from hop_design.serialization import canonical_json_bytes

runner = CliRunner()


def test_cli_reports_distribution_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "hop-design 0.1.0a0"


def test_cli_compiles_and_reports_visible_default(tmp_path: Path) -> None:
    output = tmp_path / "demo"

    result = runner.invoke(
        app,
        [
            "compile",
            "--sequence",
            "NRY",
            "--design-id",
            "demo",
            "--out",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "hop:defaults/generic-direct-synthesis@1" in result.output
    assert "hop:plan/demo/" in result.output
    verify_bundle(output)


def test_cli_dry_run_validates_without_writing(tmp_path: Path) -> None:
    output = tmp_path / "demo"

    result = runner.invoke(
        app,
        [
            "compile",
            "--sequence",
            "ACGT",
            "--design-id",
            "demo",
            "--out",
            str(output),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    assert not output.exists()


def test_cli_rejects_rna_input(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["compile", "--sequence", "AUGC", "--out", str(tmp_path / "demo")],
    )

    assert result.exit_code != 0
    assert "invalid symbols: U" in result.output


def test_cli_compiles_a_strict_file_spec(tmp_path: Path) -> None:
    output = tmp_path / "from-spec"
    spec_path = tmp_path / "design.json"
    spec_path.write_bytes(canonical_json_bytes(create_spec(sequence="NN", design_id="from-spec")))

    result = runner.invoke(
        app,
        ["compile", "--spec", str(spec_path), "--out", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert "hop:plan/from-spec/" in result.output
    verify_bundle(output)


def test_cli_rejects_ambiguous_sequence_and_spec_inputs(tmp_path: Path) -> None:
    spec_path = tmp_path / "design.json"
    spec_path.write_bytes(canonical_json_bytes(create_spec(sequence="NN", design_id="from-spec")))

    result = runner.invoke(
        app,
        [
            "compile",
            "--sequence",
            "ACGT",
            "--spec",
            str(spec_path),
            "--out",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code != 0
    assert "exactly one" in result.output
