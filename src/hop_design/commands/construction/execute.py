"""Execute an explicitly bounded construction request through the public facade."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def construction_execute_command(
    request: Annotated[Path, typer.Argument(help="Strict product request JSON or YAML.")],
    output: Annotated[Path, typer.Option("--out", help="New outcome directory.")],
    design_id: Annotated[
        str,
        typer.Option(
            "--design-id",
            help=(
                "1-64 lowercase letters, digits, dot, underscore or hyphen; "
                "start with a letter or digit."
            ),
        ),
    ],
    continuation: Annotated[
        str, typer.Option("--continuation", help="Explicit policy: sole-witness.")
    ],
) -> None:
    """Obtain a preparation or a scoped failure without relaxing the request."""
    try:
        if continuation != "sole-witness":
            raise ValueError("Continuation must be explicitly 'sole-witness'.")
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing execution path: {output}")
        execution = construction.execute_construction_request(
            request, design_id=design_id, continuation="sole-witness"
        )
        execution.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--design-id/--out") from error
    typer.echo(execution.report_text)
    typer.echo(f"Outcome: {output / 'summary.json'}")
