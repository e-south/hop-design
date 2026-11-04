"""Adapt comparison intent to the file-oriented public facade."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def preview_comparison_command(
    request: Annotated[Path, typer.Argument(help="Molecular comparison brief.")],
    output: Annotated[Path, typer.Option("--out", help="New comparison preview directory.")],
) -> None:
    """Show required members, inherited permissions and explicit conflicts."""
    try:
        _new_output(output)
        packet = construction.prepare_scaffold_comparison(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)


def assess_comparison_command(
    request: Annotated[Path, typer.Argument(help="Molecular comparison brief.")],
    discovery: Annotated[Path, typer.Argument(help="Verified scaffold discovery packet.")],
    output: Annotated[Path, typer.Option("--out", help="New portable assessment directory.")],
) -> None:
    """Find compatible sets within existing complete options, without more molecular search."""
    try:
        _new_output(output)
        packet = construction.assess_scaffold_comparison(request, discovery)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/DISCOVERY/--out") from error
    typer.echo(packet.report_text)


def execute_comparison_command(
    request: Annotated[Path, typer.Argument(help="Molecular comparison brief with finite bounds.")],
    output: Annotated[Path, typer.Option("--out", help="New discovery and assessment directory.")],
) -> None:
    """Discover complete preparations and assess the requested molecular comparison."""
    try:
        _new_output(output)
        packet = construction.execute_scaffold_comparison(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)


def select_comparison_command(
    comparison: Annotated[Path, typer.Argument(help="Saved portable comparison assessment.")],
    set_label: Annotated[str, typer.Option("--set", help="Explicit displayed set label.")],
    baseline: Annotated[str, typer.Option(help="Required member used as the comparison baseline.")],
    output: Annotated[Path, typer.Option("--out", help="New named preparation set directory.")],
) -> None:
    """Retrieve an explicitly chosen set without copying construction identities or paths."""
    try:
        _new_output(output)
        packet = construction.select_scaffold_comparison(
            comparison, set_label=set_label, baseline=baseline
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(
            str(error), param_hint="COMPARISON/--set/--baseline/--out"
        ) from error
    typer.echo(packet.report_text)


def _new_output(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to replace existing output: {path}")
