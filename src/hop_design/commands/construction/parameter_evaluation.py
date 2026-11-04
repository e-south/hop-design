"""Public bounded evaluation adapter; parameter and preservation semantics stay in HOP."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def evaluate_parameters_command(
    options: Annotated[Path, typer.Argument(help="Verified original or extended exploration.")],
    choices: Annotated[Path, typer.Argument(help="Saved parameter query result packet.")],
    output: Annotated[Path, typer.Option("--out", help="New extended exploration directory.")],
    max_branches: Annotated[
        int, typer.Option(min=1, max=64, help="Maximum newly evaluated branches.")
    ],
    max_continuations: Annotated[
        int, typer.Option(min=1, max=64, help="Maximum continuations per branch.")
    ],
) -> None:
    """Evaluate a selected parameter region and retain the original complete preparations."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        pool = construction.load_scaffold_exploration(options)
        query = construction.load_scaffold_variant_choices(pool, choices)
        result = construction.evaluate_scaffold_parameters(
            pool, query, max_branches=max_branches, max_continuations_per_branch=max_continuations
        )
        result.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/CHOICES/bounds/--out") from error
    typer.echo(result.report_text)
