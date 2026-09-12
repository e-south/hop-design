"""Named method commands for callers with their own execution environments."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design.api import (
    compile_linear_source_method_file,
    resolve_linear_source_method_file,
    verify_linear_source_method_file,
)

method_app = typer.Typer(
    help="Resolve, publish, and replay linear-source method artifacts.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


@method_app.command("resolve-linear-source")
def resolve_command(request: Path) -> None:
    """Resolve one request, retaining expected infeasibility as an explicit outcome."""
    try:
        typer.echo(resolve_linear_source_method_file(request))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


@method_app.command("compile-linear-source")
def compile_command(request: Path, output: Annotated[Path, typer.Option("--out")]) -> None:
    """Compile and publish one complete method bundle to a new directory."""
    try:
        typer.echo(compile_linear_source_method_file(request, output))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


@method_app.command("verify-linear-source")
def verify_command(bundle: Path) -> None:
    """Verify all retained bundle bytes and replay the declared method."""
    try:
        typer.echo(verify_linear_source_method_file(bundle))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
