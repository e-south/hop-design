"""Command-line interface for the public HOP operations."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import ValidationError

from hop_design.api import compile as compile_design
from hop_design.design.compile import UnknownCatalogReferenceError
from hop_design.design.loading import load_spec
from hop_design.models.diagnostics import InfeasibleDesignError
from hop_design.models.sequence import SequenceValidationError

app = typer.Typer(
    help="Compile one input sequence or strict file spec into a checked HOP Design bundle.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


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
        Path,
        typer.Option("--out", help="New directory that will receive the portable bundle."),
    ],
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
        typer.Option("--dry-run", help="Validate and compile without writing files."),
    ] = False,
) -> None:
    """Compile one bounded design from exactly one input surface."""
    try:
        if (sequence is None) == (spec_path is None):
            raise typer.BadParameter(
                "Provide exactly one of --sequence or --spec.",
                param_hint="--sequence/--spec",
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
            compilation.write(output)
    except typer.BadParameter:
        raise
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc), param_hint="--out") from exc
    except (
        InfeasibleDesignError,
        OSError,
        SequenceValidationError,
        ValidationError,
        UnknownCatalogReferenceError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        raise typer.BadParameter(str(exc), param_hint="--sequence/--spec") from exc

    typer.echo(f"Default: {compilation.spec.defaults_ref}")
    typer.echo(f"Plan: {compilation.plan.plan_id}")
    typer.echo(f"Bundle: {compilation.bundle.bundle_id}")
    if dry_run:
        typer.echo("Dry run: bundle validated; no files written.")
    else:
        typer.echo(f"Wrote: {output}")


if __name__ == "__main__":
    app()
