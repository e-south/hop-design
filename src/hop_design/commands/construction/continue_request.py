"""Continue a saved authored request with explicit local realization identities."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def construction_continue_command(
    request: Annotated[Path, typer.Argument(help="Original strict product request JSON or YAML.")],
    design_id: Annotated[str, typer.Option("--design-id")],
    foldback: Annotated[
        Path, typer.Option("--foldback", help="Replay-verified foldback result JSON.")
    ],
    foldback_realization_id: Annotated[str, typer.Option("--foldback-realization-id")],
    output: Annotated[Path, typer.Option("--out", help="New outcome directory.")],
    basal: Annotated[Path | None, typer.Option("--basal")] = None,
    basal_realization_id: Annotated[str | None, typer.Option("--basal-realization-id")] = None,
) -> None:
    """Use exact local choices while retaining every authored request requirement."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing execution path: {output}")
        execution = construction.continue_construction_request(
            request,
            design_id=design_id,
            foldback_path=foldback,
            foldback_realization_id=foldback_realization_id,
            basal_path=basal,
            basal_realization_id=basal_realization_id,
        )
        execution.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(
            str(error), param_hint="REQUEST/selection/--design-id/--out"
        ) from error
    typer.echo(execution.report_text)
    typer.echo(f"Outcome: {output / 'summary.json'}")
