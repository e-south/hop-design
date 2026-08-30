from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design.api import create_spec, verify_bundle
from hop_design.cli import app
from hop_design.serialization import canonical_json_bytes
from tests.support.claim_language import assert_no_positive_downstream_claims

runner = CliRunner()


def test_cli_reports_distribution_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == f"hop-design {version('hop-design')}"


@pytest.mark.parametrize(
    "arguments",
    (
        ("--help",),
        ("compile", "--help"),
        ("verify", "--help"),
        ("space", "--help"),
        ("space", "preview", "--help"),
        ("space", "compile", "--help"),
    ),
)
def test_default_cli_help_does_not_make_positive_downstream_claims(
    arguments: tuple[str, ...],
) -> None:
    result = runner.invoke(app, list(arguments))

    assert result.exit_code == 0, result.output
    assert_no_positive_downstream_claims(result.output, surface="CLI help")


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
    assert "Dry run: design derivation verified; no files written." in result.output
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
    assert "Dry run: design derivation verified; no files written." in result.output


def test_default_cli_receipts_do_not_make_positive_downstream_claims(tmp_path: Path) -> None:
    dry_run = runner.invoke(
        app,
        ["compile", "--sequence", "ACGT", "--design-id", "receipt", "--dry-run"],
    )
    assert dry_run.exit_code == 0, dry_run.output

    spec_path = tmp_path / "space.yaml"
    spec_path.write_text(
        "schema: hop/substrate-space/v1\nname: receipt-space\npayload:\n  - fixed: ACGT\n",
        encoding="utf-8",
    )
    preview = runner.invoke(app, ["space", "preview", str(spec_path)])
    assert preview.exit_code == 0, preview.output
    output = tmp_path / "compiled-space"
    compiled = runner.invoke(
        app,
        ["space", "compile", str(spec_path), "--out", str(output)],
    )
    assert compiled.exit_code == 0, compiled.output
    verified = runner.invoke(app, ["verify", str(output / "bundle")])
    assert verified.exit_code == 0, verified.output

    for receipt in (dry_run.output, preview.output, compiled.output, verified.output):
        assert_no_positive_downstream_claims(receipt, surface="CLI receipt")


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


def _write_space_spec(path: Path, *, variable: str = "N") -> None:
    path.write_text(
        f"""schema: hop/substrate-space/v1
name: cli-space
question: Which paired context changes activity?
payload:
  - fixed: ACTG
  - variable: {variable}
    label: context
  - fixed: GATC
    label: recognition-site
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
    assert "Domains: N=A/C/G/T" in result.output
    assert "4 exact designs" in result.output
    assert "Ready for exhaustive digital compilation" in result.output
    assert "HOP will use the versioned standard hairpin context." in result.output
    assert "Physical construction and activity are outside this preview." in result.output
    assert {path.name for path in tmp_path.iterdir()} == {"space.yaml"}


def test_cli_previews_actual_mixed_iupac_domains_and_cardinality_factors(
    tmp_path: Path,
) -> None:
    spec_path = tmp_path / "space.yaml"
    _write_space_spec(spec_path, variable="RYN")

    result = runner.invoke(app, ["space", "preview", str(spec_path)])

    assert result.exit_code == 0, result.output
    assert "Payload: ACTG RYN GATC" in result.output
    assert "Domains: R=A/G · Y=C/T · N=A/C/G/T" in result.output
    assert "16 exact designs (2 \u00d7 2 \u00d7 4)" in result.output


def test_cli_reports_the_invalid_space_field_and_supported_dna_iupac_codes(
    tmp_path: Path,
) -> None:
    spec_path = tmp_path / "invalid.yaml"
    _write_space_spec(spec_path, variable="ZNN")

    result = runner.invoke(app, ["space", "preview", str(spec_path)])

    assert result.exit_code != 0
    assert "payload.1.variable" in result.output
    assert "invalid symbols: Z" in result.output
    assert "Use A, C, G, T, R, Y, S, W, K, M, B, D, H, V, or N." in result.output
    assert "Traceback" not in result.output


def test_cli_previews_a_blocked_space_as_a_successful_read_only_result(tmp_path: Path) -> None:
    spec_path = tmp_path / "blocked.yaml"
    _write_space_spec(spec_path, variable="NNNNN")

    result = runner.invoke(app, ["space", "preview", str(spec_path)])

    assert result.exit_code == 0, result.output
    assert "valid specification defines 1,024 exact assignments" in result.output
    assert "Compilation supports up to 256 designs in this release." in result.output
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
    assert "Compiled and verified 4 exact designs." in result.output
    assert "Coverage: 4/4 complete · 4 unique · 0 duplicates" in result.output
    assert "Digital verification: passed" in result.output
    assert (
        f"Substrate-space projection: {output / 'figures' / '01-substrate-space.svg'}"
        in result.output
    )
    assert f"Design-set diagnostic: {output / 'figures' / '02-design-set.svg'}" in result.output
    assert f"Evidence receipt: {output / 'handoff' / 'scientific-receipt.svg'}" in result.output
    assert f"FASTA: {output / 'sequences.fasta'}" in result.output
    assert "No physical construction, QC, or activity record is attached." in result.output

    verify_result = runner.invoke(app, ["verify", str(output / "bundle")])
    assert verify_result.exit_code == 0, verify_result.output
    assert "Verified design set: hop:design-set/" in verify_result.output
    assert "Coverage: complete · 4 exact designs" in verify_result.output


def test_verify_help_names_its_design_bundle_scope() -> None:
    result = runner.invoke(app, ["verify", "--help"])

    assert result.exit_code == 0, result.output
    assert "Verify a HOP design or design-set bundle." in result.output
    assert "portable digital authority" not in result.output
