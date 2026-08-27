from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

from typer.testing import CliRunner

from hop_design.api import create_spec, verify_bundle
from hop_design.cli import app
from hop_design.serialization import canonical_json_bytes

runner = CliRunner()


def test_cli_reports_distribution_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == f"hop-design {version('hop-design')}"


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
    assert "hop:defaults/generic-hairpin-design@2" in result.output
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


def test_cli_dry_run_does_not_require_an_output_path() -> None:
    result = runner.invoke(
        app,
        [
            "compile",
            "--sequence",
            "ACGT",
            "--design-id",
            "demo",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output


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


def _write_space_spec(path: Path, *, variable: str = "N", max_members: int = 4) -> None:
    path.write_text(
        f"""schema: hop/substrate-space/v1
name: cli-space
context:
  question: Which paired context changes activity?
payload:
  segments:
    - fixed: ACTG
    - variable: {variable}
      name: context
    - fixed: GATC
      name: recognition-site
hairpin:
  defaults_ref: hop:defaults/generic-hairpin-design@2
enumeration:
  mode: exhaustive
  max_members: {max_members}
""",
        encoding="utf-8",
    )


def test_cli_previews_a_ready_substrate_space_without_writing(tmp_path: Path) -> None:
    spec_path = tmp_path / "space.yaml"
    _write_space_spec(spec_path)

    result = runner.invoke(app, ["space", "preview", str(spec_path)])

    assert result.exit_code == 0, result.output
    assert "Substrate space: cli-space" in result.output
    assert "Payload: ACTG N GATC" in result.output
    assert "Variable positions: 5" in result.output
    assert "Space: 4 exact variants" in result.output
    assert "Compilation: ready" in result.output
    assert "Construction, QC, and activity: not evaluated" in result.output
    assert {path.name for path in tmp_path.iterdir()} == {"space.yaml"}


def test_cli_previews_a_blocked_space_as_a_successful_read_only_result(tmp_path: Path) -> None:
    spec_path = tmp_path / "blocked.yaml"
    _write_space_spec(spec_path, variable="NNNNNN", max_members=256)

    result = runner.invoke(app, ["space", "preview", str(spec_path)])

    assert result.exit_code == 0, result.output
    assert "valid specification defines 4,096 variants" in result.output
    assert (
        "Preview completed. No designs were enumerated and no files were written." in result.output
    )


def test_cli_compiles_and_verifies_a_complete_design_set(tmp_path: Path) -> None:
    spec_path = tmp_path / "space.yaml"
    output = tmp_path / "compiled"
    _write_space_spec(spec_path)

    result = runner.invoke(
        app,
        ["space", "compile", str(spec_path), "--out", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert "Compiled 4 of 4 exact designs." in result.output
    assert f"Verified design package: {output / 'bundle'}" in result.output
    assert "Physical construction, QC, and biological activity were not evaluated." in result.output

    verify_result = runner.invoke(app, ["verify", str(output / "bundle")])
    assert verify_result.exit_code == 0, verify_result.output
    assert "Verified design set: hop:design-set/cli-space/" in verify_result.output
    assert "Coverage: complete · 4 exact designs" in verify_result.output
