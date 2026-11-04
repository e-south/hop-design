"""Required sets within saved conditional choices; no new molecular search."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def compare_variants_command(
    options: Annotated[Path, typer.Argument(help="Verified discovery or molecular edit result.")],
    choices: Annotated[Path, typer.Argument(help="Saved conditional choices packet.")],
    request: Annotated[
        Path, typer.Argument(help="Required members, controls and explicit grouping bounds.")
    ],
    output: Annotated[Path, typer.Option("--out", help="New comparison assessment directory.")],
) -> None:
    """Find compatible member groups without selecting a reference or preparation."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        pool = construction.load_scaffold_exploration(options)
        current = construction.load_scaffold_variant_choices(pool, choices)
        result = construction.compare_scaffold_variants(pool, current, request)
        result.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/CHOICES/REQUEST/--out") from error
    typer.echo(result.report_text)


def select_variant_comparison_command(
    options: Annotated[Path, typer.Argument(help="Original verified discovery or edit result.")],
    comparison: Annotated[Path, typer.Argument(help="Saved required comparison assessment.")],
    set_label: Annotated[str, typer.Option("--set", help="Explicit compatible set label.")],
    baseline: Annotated[str, typer.Option(help="Explicit member name for presentation.")],
    output: Annotated[Path, typer.Option("--out", help="New portable preparation directory.")],
) -> None:
    """Recheck required membership, controls and material requirements before retrieval."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        result = construction.select_scaffold_variant_comparison(
            options, comparison, set_label=set_label, baseline=baseline
        )
        result.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(
            str(error), param_hint="OPTIONS/COMPARISON/selection/--out"
        ) from error
    typer.echo(result.report_text)
