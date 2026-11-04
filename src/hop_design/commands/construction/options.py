"""Product-first exploration, comparative grouping and explicit retrieval."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def explore_command(
    request: Annotated[Path, typer.Argument(help="Product request with bounded geometry domains.")],
    output: Annotated[Path, typer.Option("--out", help="New options directory.")],
    max_continuations: Annotated[int, typer.Option(help="Explicit pair budget, 1-64.")],
) -> None:
    """See complete scaffold options before selecting construction details."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        packet = construction.explore_construction_options(
            request, max_continuations=max_continuations
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(
            str(error), param_hint="REQUEST/--max-continuations/--out"
        ) from error
    typer.echo(packet.report_text)
    typer.echo(f"Complete options: {output / 'report.md'}")


def option_sets_command(
    options: Annotated[Path, typer.Argument(help="Saved complete options packet.")],
    comparison: Annotated[Path, typer.Argument(help="Requested dimensions and shared controls.")],
    output: Annotated[Path, typer.Option("--out", help="New comparative groups directory.")],
) -> None:
    """Find available comparative sets without choosing a reference or changing the request."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        packet = construction.find_construction_option_sets(options, comparison)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/COMPARISON/--out") from error
    typer.echo(packet.report_text)


def select_options_command(
    options: Annotated[Path, typer.Argument(help="Saved complete options packet.")],
    output: Annotated[Path, typer.Option("--out", help="New portable preparation set.")],
    option: Annotated[
        list[str], typer.Option(help="Chosen visible label; repeat for each member.")
    ],
    baseline: Annotated[str, typer.Option(help="Explicit reference label among selected options.")],
    shared: Annotated[
        list[str] | None, typer.Option(help="Required shared property; repeat.")
    ] = None,
    compare: Annotated[list[str] | None, typer.Option(help="Compared property; repeat.")] = None,
    comparison: Annotated[
        Path | None, typer.Option(help="Reuse the comparison intent used for option-sets.")
    ] = None,
) -> None:
    """Retrieve exact chosen molecules and preparation records using visible option labels."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        packet = construction.select_construction_options(
            options,
            option_labels=tuple(option),
            baseline=baseline,
            shared_properties=tuple(shared or ()),
            compared_properties=tuple(compare or ()),
            comparison=comparison,
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(
            str(error), param_hint="OPTIONS/--option/--baseline/--out"
        ) from error
    typer.echo(packet.report_text)
