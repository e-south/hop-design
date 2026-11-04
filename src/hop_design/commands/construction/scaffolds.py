"""Preview product intent, discover complete scaffolds and retrieve named preparations."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def preview_scaffolds_command(
    request: Annotated[Path, typer.Argument(help="Scaffold discovery request.")],
    output: Annotated[Path, typer.Option("--out", help="New request preview directory.")],
) -> None:
    """Inspect desired dimensions, preparation permissions and conflicts before search."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        packet = construction.prepare_scaffold_discovery(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)


def discover_scaffolds_command(
    request: Annotated[
        Path, typer.Argument(help="Scaffold discovery request with explicit budgets.")
    ],
    output: Annotated[Path, typer.Option("--out", help="New scaffold discovery directory.")],
) -> None:
    """Evaluate permitted preparation alternatives against the requested scaffold."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        packet = construction.discover_scaffolds(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)


def select_scaffolds_command(
    options: Annotated[Path, typer.Argument(help="Saved scaffold discovery packet.")],
    output: Annotated[Path, typer.Option("--out", help="New portable preparation set.")],
    member: Annotated[
        list[str], typer.Option(help="Explicit NAME=OPTION binding; repeat per member.")
    ],
    baseline: Annotated[str, typer.Option(help="User name of an explicitly selected baseline.")],
    shared: Annotated[
        list[str] | None, typer.Option(help="Required shared property; repeat.")
    ] = None,
    compare: Annotated[list[str] | None, typer.Option(help="Compared property; repeat.")] = None,
) -> None:
    """Retrieve a named molecular comparison and its exact preparations."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        bindings = {}
        for item in member:
            name, separator, label = item.partition("=")
            if not separator or not label or name in bindings:
                raise ValueError("Each --member must be a unique NAME=OPTION binding.")
            bindings[name] = label
        packet = construction.select_scaffold_options(
            options,
            members=bindings,
            baseline=baseline,
            shared_properties=tuple(shared or ()),
            compared_properties=tuple(compare or ()),
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(
            str(error), param_hint="OPTIONS/--member/--baseline/--out"
        ) from error
    typer.echo(packet.report_text)
