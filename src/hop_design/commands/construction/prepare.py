"""Translate authored product intent through the shared public API."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def construction_prepare_command(
    request: Annotated[Path, typer.Argument(help="Strict hop.product-request/v1 JSON or YAML.")],
    output: Annotated[Path, typer.Option("--out", help="New directory for expanded inputs.")],
    compare_to: Annotated[
        Path | None,
        typer.Option(
            "--compare-to", help="Explicit reference request for an unevaluated edit preview."
        ),
    ] = None,
) -> None:
    """Translate a product request into explicit construction inputs."""
    try:
        prepared = construction.prepare_construction_request(request, compare_to=compare_to)
        prepared.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(prepared.report_text)
    typer.echo(f"Construction input: {output / 'construction.json'}")
