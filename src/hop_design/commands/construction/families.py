"""Preview, execute and explicitly select finite scaffold families."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def author_family_command(
    request: Annotated[Path, typer.Argument(help="Concise hop.scaffold-comparison/v1 brief.")],
    output: Annotated[
        Path, typer.Option("--out", help="New family request and preview directory.")
    ],
) -> None:
    """Specify product, varied dimensions, shared properties and explicit permissions."""
    try:
        packet = construction.author_construction_family(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)
    typer.echo(f"Canonical family: {output / 'family.json'}")


def prepare_family_command(
    request: Annotated[Path, typer.Argument(help="Strict hop.construction-family/v1 request.")],
    output: Annotated[Path, typer.Option("--out", help="New preview directory.")],
) -> None:
    """See effective member constraints and conflicts before running any search."""
    try:
        packet = construction.prepare_construction_family(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)
    typer.echo(f"Preview: {output / 'summary.json'}")


def execute_family_command(
    request: Annotated[Path, typer.Argument(help="Strict hop.construction-family/v1 request.")],
    output: Annotated[Path, typer.Option("--out", help="New directory containing every outcome.")],
    continuation: Annotated[
        str, typer.Option("--continuation", help="Explicit policy: sole-witness.")
    ],
) -> None:
    """Generate complete alternatives and retain failed or unresolved member requests."""
    try:
        if continuation != "sole-witness":
            raise ValueError("Continuation must be explicitly 'sole-witness'.")
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing family path: {output}")
        packet = construction.execute_construction_family(request, continuation="sole-witness")
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out/--continuation") from error
    typer.echo(packet.report_text)
    typer.echo(f"Family: {output / 'summary.json'}")


def select_set_command(
    request: Annotated[Path, typer.Argument(help="Explicit hop.construction-set/v1 membership.")],
    output: Annotated[Path, typer.Option("--out", help="New comparative preparation directory.")],
) -> None:
    """Retrieve exact preparations and consolidate chemically identical order specifications."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing set path: {output}")
        packet = construction.select_construction_set(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)
    typer.echo(f"Set: {output / 'summary.json'}")


def reconcile_family_command(
    family: Annotated[Path, typer.Argument(help="Saved family; preserved in the revision.")],
    source_member: Annotated[str, typer.Option(help="Original member being continued or edited.")],
    outcome: Annotated[Path, typer.Option(help="Explicitly completed request outcome directory.")],
    output: Annotated[Path, typer.Option("--out", help="New revised family directory.")],
    member: Annotated[
        str | None, typer.Option(help="New member name for an edited request.")
    ] = None,
    revised_request: Annotated[
        Path | None, typer.Option(help="Revised family request retaining the original roster.")
    ] = None,
    preferred_loop_nt: Annotated[
        int | None,
        typer.Option(help="Record a declared loop preference; selected product must match."),
    ] = None,
) -> None:
    """Reconcile an exact continuation or a separately named edited alternative."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing family path: {output}")
        packet = construction.reconcile_construction_family(
            family,
            source_member=source_member,
            outcome_path=outcome,
            member=member,
            revised_request=revised_request,
            preferred_loop_nt=preferred_loop_nt,
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="FAMILY/--outcome/--out") from error
    typer.echo(f"Revised family: {output / 'summary.json'}")
    typer.echo(f"Original family: {output / 'history/parent'}")


def report_family_command(
    family: Annotated[Path, typer.Argument(help="Saved executed family packet.")],
    output: Annotated[Path, typer.Option("--out", help="New portable comparison report.")],
    selection: Annotated[
        Path | None, typer.Option("--selection", help="Explicit comparative-set request.")
    ] = None,
    baseline: Annotated[
        str | None, typer.Option("--baseline", help="Named complete comparison reference.")
    ] = None,
    edit: Annotated[
        list[str] | None,
        typer.Option("--edit", help="Explicit SOURCE:TARGET request edit; repeatable."),
    ] = None,
) -> None:
    """See requested and obtained scaffolds, all outcomes and exact preparations."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing report path: {output}")
        edits = []
        for value in edit or []:
            pair = value.split(":")
            if len(pair) != 2:
                raise ValueError("--edit must be SOURCE:TARGET member names.")
            edits.append((pair[0], pair[1]))
        packet = construction.project_construction_family_report(
            family, selection=selection, baseline=baseline, edits=tuple(edits)
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="FAMILY/--selection/--out") from error
    typer.echo(f"Scaffold comparison: {output / 'report.pdf'}")
    typer.echo(f"Preparations and details: {output / 'report.md'}")
