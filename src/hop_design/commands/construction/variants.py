"""Thin adapters for finite conditional exploration and intent-preserving retrieval."""

import json
from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def inspect_variant_command(
    options: Annotated[Path, typer.Argument(help="Verified discovery or molecular edit result.")],
    choices: Annotated[Path, typer.Argument(help="Saved conditional choices packet.")],
    option: Annotated[str, typer.Option(help="Explicit complete preparation label.")],
    state: Annotated[
        str, typer.Option(help="hairpin, endpoint, source_material or listed state ID.")
    ],
    output: Annotated[Path, typer.Option("--out", help="New inspection directory.")],
    focus: Annotated[Path | None, typer.Option(help="Saved molecular address JSON.")] = None,
) -> None:
    """Inspect a state without changing molecular constraints or selecting a product."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        pool = construction.load_scaffold_exploration(options)
        admitted = construction.load_scaffold_variant_choices(pool, choices)
        request = {
            "result_digest": pool.result_digest,
            "query_digest": json.loads(admitted.json_bytes)["query_digest"],
            "option_label": option,
            "state": state,
        }
        if focus is not None:
            request["focus"] = json.loads(focus.read_bytes())
        packet = construction.inspect_scaffold_variant(pool, admitted, request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(
            str(error), param_hint="OPTIONS/CHOICES/inspection/--out"
        ) from error
    typer.echo(packet.report_text)


def variants_command(
    options: Annotated[Path, typer.Argument(help="Verified discovery or molecular edit result.")],
    output: Annotated[Path, typer.Option("--out", help="New conditional choices directory.")],
    query: Annotated[
        Path | None, typer.Option(help="Exact saved query; includes pins and controls.")
    ] = None,
    stage: Annotated[str | None, typer.Option(help="Molecular stage: hairpin or endpoint.")] = None,
    focus: Annotated[
        str | None, typer.Option(help="loop, closing, assembly, stem or interfaces.")
    ] = None,
    reference: Annotated[str | None, typer.Option(help="Fixed complete option label.")] = None,
    preserve: Annotated[
        list[str] | None, typer.Option(help="STAGE:PROPERTY to preserve; repeat.")
    ] = None,
) -> None:
    """List supported neighborhood variants without searching or choosing a product."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        if query is not None and any(v is not None for v in (stage, focus, reference, preserve)):
            raise ValueError("Use --query or explicit stage/focus/reference/controls, not both.")
        if query is None and (stage is None or focus is None):
            raise ValueError("Specify --stage and --focus, or provide --query.")
        pool = construction.load_scaffold_exploration(options)
        controls = []
        for value in preserve or ():
            molecular_stage, sep, prop = value.partition(":")
            if not sep:
                raise ValueError("Preserved properties use STAGE:PROPERTY.")
            controls.append({"stage": molecular_stage, "property": prop})
        request = (
            query
            if query is not None
            else {
                "result_digest": pool.result_digest,
                "stage": stage,
                "focus": focus,
                "reference": reference,
                "controls": controls,
            }
        )
        packet = construction.query_scaffold_variants(pool, request)
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/query/--out") from error
    typer.echo(packet.report_text)


def select_variants_command(
    options: Annotated[Path, typer.Argument(help="Original verified result packet.")],
    choices: Annotated[Path, typer.Argument(help="Saved conditional choices packet.")],
    output: Annotated[Path, typer.Option("--out", help="New portable preparation set.")],
    member: Annotated[list[str], typer.Option(help="Explicit NAME=OPTION binding; repeat.")],
    baseline: Annotated[str, typer.Option(help="Explicit selected member name for comparison.")],
) -> None:
    """Reverify all exploration constraints before retrieving the named preparations."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        members = {}
        for item in member:
            name, sep, label = item.partition("=")
            if not sep or not name or not label or name in members:
                raise ValueError("Each member must be a unique NAME=OPTION binding.")
            members[name] = label
        packet = construction.select_scaffold_variants(
            options, choices, members=members, baseline=baseline
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(
            str(error), param_hint="OPTIONS/CHOICES/selection/--out"
        ) from error
    typer.echo(packet.report_text)
