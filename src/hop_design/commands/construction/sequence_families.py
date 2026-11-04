"""Public adapters for bounded exact-member sequence families."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def preview_sequence_family_command(
    request: Annotated[Path, typer.Argument(help="Bounded symbolic-stem family request.")],
    output: Annotated[Path, typer.Option("--out", help="New exact-member preview directory.")],
) -> None:
    """Expand required exact stems without searching or authoring their paired arms."""
    try:
        packet = construction.prepare_sequence_family(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)


def evaluate_sequence_family_command(
    request: Annotated[Path, typer.Argument(help="Bounded symbolic-stem family request.")],
    output: Annotated[Path, typer.Option("--out", help="New complete family options directory.")],
) -> None:
    """Evaluate all required exact members; retain failures and per-member search coverage."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        packet = construction.execute_sequence_family(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)


def select_sequence_family_command(
    options: Annotated[Path, typer.Argument(help="Evaluated sequence-family packet.")],
    output: Annotated[Path, typer.Option("--out", help="New verified portable family set.")],
    member: Annotated[
        list[str], typer.Option(help="Required MEMBER=OPTION; repeat for all members.")
    ],
    baseline: Annotated[str, typer.Option(help="Explicit comparison reference member.")],
) -> None:
    """Verify required membership, shared flanks and specified material reuse before retrieval."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        members = {}
        for item in member:
            name, sep, label = item.partition("=")
            if not sep or not label or name in members:
                raise ValueError("Each member must be a distinct MEMBER=OPTION binding.")
            members[name] = label
        packet = construction.select_sequence_family(options, members=members, baseline=baseline)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/selection/--out") from error
    typer.echo(packet.report_text)
