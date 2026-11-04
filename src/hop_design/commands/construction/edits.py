"""Thin CLI adapters for explicit edits and verified preparation retrieval."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def prepare_edit_command(
    request: Annotated[Path, typer.Argument(help="Original scaffold discovery request.")],
    output: Annotated[Path, typer.Option("--out", help="New molecular edit preview directory.")],
    loop: Annotated[
        list[str] | None, typer.Option(help="Exact required loop word; repeat for a comparison.")
    ] = None,
    placement: Annotated[
        list[str] | None, typer.Option(help="LEFT_BP:RIGHT_BP paired gaps; repeat.")
    ] = None,
    left_end: Annotated[
        str | None, typer.Option(help="Left end, on its protruding strand 5'-3'.")
    ] = None,
    right_end: Annotated[
        str | None, typer.Option(help="Right end, on its protruding strand 5'-3'.")
    ] = None,
    basal_nick: Annotated[
        list[str] | None, typer.Option(help="Permitted characterized basal nickase ID; repeat.")
    ] = None,
    release: Annotated[
        list[str] | None, typer.Option(help="Permitted characterized release enzyme ID; repeat.")
    ] = None,
) -> None:
    """Author a bound molecular edit and preview inherited conflicts without searching."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        if (left_end is None) != (right_end is None):
            raise ValueError("Specify both --left-end and --right-end, or preserve both.")
        placements = None
        if placement is not None:
            pairs = [item.split(":") for item in placement]
            if any(len(pair) != 2 for pair in pairs):
                raise ValueError("Each placement must be LEFT_BP:RIGHT_BP.")
            placements = tuple((int(a), int(b)) for a, b in pairs)
        packet = construction.author_molecular_edit(
            request,
            loop_sequences=None if loop is None else tuple(loop),
            end_placements=placements,
            end_words=None if left_end is None or right_end is None else (left_end, right_end),
            basal_nick_enzyme_ids=None if basal_nick is None else tuple(basal_nick),
            release_enzyme_ids=None if release is None else tuple(release),
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--loop/--out") from error
    typer.echo(packet.report_text)


def preview_edit_command(
    request: Annotated[Path, typer.Argument(help="Captured molecular edit request.")],
    output: Annotated[Path, typer.Option("--out", help="New preview directory.")],
) -> None:
    """Validate an edited request and show conflicts before evaluating any molecules."""
    try:
        packet = construction.prepare_molecular_edit(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)


def evaluate_edit_command(
    request: Annotated[Path, typer.Argument(help="Captured molecular edit request.")],
    output: Annotated[Path, typer.Option("--out", help="New evaluated alternatives directory.")],
) -> None:
    """Evaluate complete preparations under the captured edit's unchanged permissions."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        packet = construction.execute_molecular_edit(request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out") from error
    typer.echo(packet.report_text)


def select_edit_command(
    options: Annotated[Path, typer.Argument(help="Evaluated molecular edit packet.")],
    output: Annotated[Path, typer.Option("--out", help="New portable preparation set.")],
    edit_digest: Annotated[
        str, typer.Option(help="Exact evaluated edit digest; rejects stale choices.")
    ],
    member: Annotated[list[str], typer.Option(help="Explicit NAME=OPTION binding; repeat.")],
    baseline: Annotated[
        str, typer.Option(help="Name of the explicitly selected comparison reference.")
    ],
    shared: Annotated[
        list[str] | None, typer.Option(help="Required shared property; repeat.")
    ] = None,
    compare: Annotated[list[str] | None, typer.Option(help="Compared property; repeat.")] = None,
) -> None:
    """Retrieve explicit choices, preserving molecular identities and exact oligo roles."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        members = {}
        for item in member:
            name, sep, label = item.partition("=")
            if not sep or not label or name in members:
                raise ValueError("Each member must be a unique NAME=OPTION binding.")
            members[name] = label
        packet = construction.select_molecular_edit(
            options,
            edit_digest=edit_digest,
            members=members,
            baseline=baseline,
            shared_properties=tuple(shared or ()),
            compared_properties=tuple(compare or ()),
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/selection/--out") from error
    typer.echo(packet.report_text)
