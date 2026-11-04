"""Bounded alternatives against a user-declared complete family reference."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def match_family_command(
    family: Annotated[Path, typer.Argument(help="Saved executed or reconciled family.")],
    output: Annotated[Path, typer.Option("--out", help="New matching packet directory.")],
    reference_member: Annotated[str, typer.Option(help="Explicit complete reference member.")],
    reference_choice: Annotated[int, typer.Option(help="Zero-based complete reference choice.")],
    max_continuations: Annotated[
        int, typer.Option(help="Maximum witness pairs to continue, 1-64.")
    ],
) -> None:
    """Find compatible preparations without relaxing requirements or selecting a set."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing matching path: {output}")
        packet = construction.match_construction_family(
            family,
            reference_member=reference_member,
            reference_choice=reference_choice,
            max_continuations=max_continuations,
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(
            str(error), param_hint="FAMILY/--reference-member/--out"
        ) from error
    typer.echo(packet.report_text)
    typer.echo(f"Matching choices: {output / 'summary.json'}")
