"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/cli.py

Defines the public command-line entrypoint for HOP design operations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import ValidationError

from hop_design.api import compile as compile_design
from hop_design.api import load_spec, verify_bundle
from hop_design.commands import construction_app
from hop_design.spaces import (
    SubstrateSpacePreview,
    SubstrateSpaceSpec,
    compile_space,
    load_verified_design_set,
    preview_space,
)

app = typer.Typer(
    help="Define and compile exact HOP hairpin designs and bounded substrate spaces.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
space_app = typer.Typer(
    help="Preview or compile one bounded substrate space.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
app.add_typer(space_app, name="space")
app.add_typer(construction_app, name="construction")

_SPACE_SPEC_MAX_BYTES = 1_000_000


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"hop-design {version('hop-design')}")
        raise typer.Exit


@app.callback()
def main(
    show_version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed HOP Design version and exit.",
        ),
    ] = False,
) -> None:
    """HOP Design command-line interface."""


@app.command("compile")
def compile_command(
    output: Annotated[
        Path | None,
        typer.Option("--out", help="New directory that will receive the portable bundle."),
    ] = None,
    sequence: Annotated[
        str | None,
        typer.Option(
            "--sequence",
            help="Input DNA sequence to pair; accepts exact or symbolic DNA IUPAC bases.",
        ),
    ] = None,
    spec_path: Annotated[
        Path | None,
        typer.Option(
            "--spec",
            help="Strict .json, .yaml, or .yml HOP specification.",
        ),
    ] = None,
    design_id: Annotated[
        str | None,
        typer.Option("--design-id", help="Stable caller-facing identifier for this design."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Derive the design and check constraints without writing files.",
        ),
    ] = False,
) -> None:
    """Compile one bounded design from exactly one input surface."""
    try:
        if (sequence is None) == (spec_path is None):
            raise typer.BadParameter(
                "Provide exactly one of --sequence or --spec.",
                param_hint="--sequence/--spec",
            )
        if output is None and not dry_run:
            raise typer.BadParameter(
                "--out is required unless --dry-run is used.",
                param_hint="--out",
            )
        if spec_path is not None:
            if design_id is not None:
                raise typer.BadParameter(
                    "--design-id is only valid with --sequence.",
                    param_hint="--design-id",
                )
            compilation = compile_design(load_spec(spec_path))
        else:
            assert sequence is not None
            compilation = compile_design(sequence=sequence, design_id=design_id)
        if not dry_run:
            assert output is not None
            compilation.write(output)
    except typer.BadParameter:
        raise
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc), param_hint="--out") from exc
    except (
        OSError,
        ValidationError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        raise typer.BadParameter(str(exc), param_hint="--sequence/--spec") from exc

    typer.echo(f"Default: {compilation.spec.defaults_ref}")
    typer.echo(f"Plan: {compilation.plan.plan_id}")
    typer.echo(f"Bundle: {compilation.bundle.bundle_id}")
    if dry_run:
        typer.echo("Dry run: design derivation verified; no files written.")
    else:
        typer.echo(f"Wrote: {output}")


def _load_space_spec(path: Path) -> SubstrateSpaceSpec:
    if path.is_symlink():
        raise ValueError("Substrate-space source must not be a symlink.")
    if not path.is_file():
        raise ValueError(f"Substrate-space source is not a regular file: {path}.")
    size_bytes = path.stat().st_size
    if size_bytes > _SPACE_SPEC_MAX_BYTES:
        raise ValueError(
            f"Substrate-space source max_bytes exceeded: {size_bytes} > {_SPACE_SPEC_MAX_BYTES}."
        )
    suffix = path.suffix.lower()
    if suffix not in {".json", ".yaml", ".yml"}:
        raise ValueError("Substrate-space file extension must be .json, .yaml, or .yml.")
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Substrate-space document root must be a mapping.")
    return SubstrateSpaceSpec.model_validate(payload)


def _segment_text(spec: SubstrateSpaceSpec) -> str:
    return " ".join(segment.fixed or segment.variable or "" for segment in spec.payload)


def _position_text(positions: tuple[int, ...]) -> str:
    if not positions:
        return "none"
    if positions == tuple(range(positions[0], positions[-1] + 1)) and len(positions) > 1:
        return f"{positions[0]}\u2013{positions[-1]}"
    return ", ".join(str(position) for position in positions)


def _variable_symbols(spec: SubstrateSpaceSpec) -> tuple[str, ...]:
    return tuple(
        symbol
        for segment in spec.payload
        if segment.variable is not None
        for symbol in segment.variable
    )


def _print_ready_preview(
    spec: SubstrateSpaceSpec,
    preview: SubstrateSpacePreview,
) -> None:
    typer.echo(f"Substrate space: {spec.name}")
    typer.echo(f"Payload: {_segment_text(spec)}")
    typer.echo(f"Variable positions: {_position_text(preview.variable_positions)}")
    typer.echo(
        "Domains: "
        + " · ".join(
            f"{symbol}={'/'.join(domain)}"
            for symbol, domain in zip(
                _variable_symbols(spec), preview.variable_domains, strict=True
            )
        )
    )
    typer.echo("Paired arm: derived automatically by reverse complement")
    factors = " \u00d7 ".join(str(len(domain)) for domain in preview.variable_domains) or "1"
    typer.echo(f"{preview.theoretical_cardinality:,} exact designs ({factors})")
    typer.echo("Ready for exhaustive digital compilation")
    typer.echo("HOP will use the versioned standard hairpin context.")
    typer.echo("Physical construction and activity are outside this preview.")


@space_app.command("preview")
def preview_space_command(
    spec_path: Annotated[Path, typer.Argument(help="Substrate-space YAML or JSON file.")],
) -> None:
    """Preview one space symbolically without enumeration or writes."""
    try:
        spec = _load_space_spec(spec_path)
        preview = preview_space(spec)
    except (OSError, ValidationError, ValueError, yaml.YAMLError) as exc:
        raise typer.BadParameter(str(exc), param_hint="SPEC_PATH") from exc
    if preview.state == "invalid":
        raise typer.BadParameter(
            preview.message or "Invalid substrate space.", param_hint="SPEC_PATH"
        )
    if preview.state == "blocked":
        typer.echo(
            f"This valid specification defines "
            f"{preview.theoretical_cardinality:,} exact assignments."
        )
        typer.echo(
            f"Compilation supports up to {preview.compilation_limit:,} designs in this release."
        )
        typer.echo("Preview completed. No designs were enumerated and no files were written.")
        typer.echo("Reduce the variable space before compilation.")
        return
    _print_ready_preview(spec, preview)


@space_app.command("compile")
def compile_space_command(
    spec_path: Annotated[Path, typer.Argument(help="Substrate-space YAML or JSON file.")],
    output: Annotated[
        Path,
        typer.Option("--out", help="New directory that will receive the design package."),
    ],
) -> None:
    """Compile and verify one complete bounded design set."""
    try:
        spec = _load_space_spec(spec_path)
        verified = compile_space(spec, destination=output)
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc), param_hint="--out") from exc
    except (OSError, ValidationError, ValueError, yaml.YAMLError) as exc:
        raise typer.BadParameter(str(exc), param_hint="SPEC_PATH") from exc
    design_set = verified.design_set
    typer.echo(f"Compiled and verified {design_set.enumerated_assignments:,} exact designs.")
    typer.echo(
        f"Coverage: {design_set.enumerated_assignments:,}/"
        f"{design_set.theoretical_cardinality:,} {design_set.coverage} · "
        f"{design_set.unique_designs:,} unique · {design_set.duplicate_count:,} duplicates"
    )
    typer.echo("Digital verification: passed")
    typer.echo(f"Substrate-space projection: {output / 'figures' / '01-substrate-space.svg'}")
    typer.echo(f"Design-set diagnostic: {output / 'figures' / '02-design-set.svg'}")
    typer.echo(f"Evidence receipt: {output / 'handoff' / 'scientific-receipt.svg'}")
    typer.echo(f"Review: {output / 'review.html'}")
    typer.echo(f"Sequence index: {output / 'designs.csv'}")
    typer.echo(f"FASTA: {output / 'sequences.fasta'}")
    typer.echo()
    typer.echo("No physical construction, QC, or activity record is attached.")


@app.command("verify")
def verify_command(
    bundle_path: Annotated[Path, typer.Argument(help="Design or design-set bundle directory.")],
) -> None:
    """Verify a HOP design or design-set bundle."""
    try:
        has_design_set = (bundle_path / "manifest.json").is_file()
        has_member = (bundle_path / "hop-bundle.json").is_file()
        if has_design_set == has_member:
            raise ValueError("Bundle must contain exactly one of manifest.json or hop-bundle.json.")
        if has_design_set:
            verified = load_verified_design_set(bundle_path)
            typer.echo(f"Verified design set: {verified.design_set.design_set_id}")
            typer.echo(
                f"Coverage: {verified.design_set.coverage} · "
                f"{verified.design_set.unique_designs:,} exact designs"
            )
        else:
            bundle = verify_bundle(bundle_path)
            typer.echo(f"Verified design: {bundle.bundle_id}")
    except (OSError, ValidationError, ValueError, yaml.YAMLError) as exc:
        raise typer.BadParameter(str(exc), param_hint="BUNDLE_PATH") from exc


if __name__ == "__main__":
    app()
