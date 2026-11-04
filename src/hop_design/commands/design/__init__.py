"""Stem-first discovery and its single selection-to-preparation lifecycle."""

import json
from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction

from .browser import create_design_server
from .common import emit, errors, intent, load_choices, write_selection
from .editions import register_edition_commands
from .feedback import execution_feedback
from .permissions import register_permission_commands
from .presentation import OutputFormat, emit_choices
from .refinement import register_refinement_commands

design_app = typer.Typer(
    help="Discover complete designs from a stem and optional molecular constraints.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

register_refinement_commands(design_app)
register_permission_commands(design_app)
register_edition_commands(design_app)


@design_app.command("resolve")
def resolve(
    output: Annotated[Path, typer.Option("--out", help="New effective-intent packet.")],
    request: Annotated[
        Path | None, typer.Option(help="Saved optional-intent JSON or YAML.")
    ] = None,
    stem: Annotated[str | None, typer.Option(help="One exact stem arm to preserve.")] = None,
    product: Annotated[str | None, typer.Option(help="Intended molecular product.")] = None,
    context: Annotated[str | None, typer.Option(help="Versioned context name or file.")] = None,
    left: Annotated[str | None, typer.Option(help="Optional exact left end word.")] = None,
    right: Annotated[str | None, typer.Option(help="Optional exact right end word.")] = None,
) -> None:
    """Inspect the effective molecular permissions without searching."""
    with errors():
        resolved = construction.resolve_design_request(
            intent(request, stem, product, context, left, right)
        )
        resolved.write(output)
        typer.echo(resolved.json_bytes.decode())


@design_app.command("discover")
def discover(
    output: Annotated[Path, typer.Option("--out", help="New portable discovery directory.")],
    request: Annotated[
        Path | None, typer.Option(help="Saved optional-intent JSON or YAML.")
    ] = None,
    stem: Annotated[str | None, typer.Option(help="One exact stem arm to preserve.")] = None,
    product: Annotated[str | None, typer.Option(help="Intended molecular product.")] = None,
    context: Annotated[str | None, typer.Option(help="Versioned context name or file.")] = None,
    left: Annotated[str | None, typer.Option(help="Optional exact left end word.")] = None,
    right: Annotated[str | None, typer.Option(help="Optional exact right end word.")] = None,
    evaluations: Annotated[
        int, typer.Option(min=1, help="Execution steps; molecular limits stay fixed.")
    ] = 64,
    first_choices: Annotated[
        int | None,
        typer.Option(min=1, help="Stop hairpin execution after this many new complete choices."),
    ] = None,
    diversify: Annotated[
        list[str] | None,
        typer.Option(
            "--diversify",
            help="Seek scaffold contrasts along this parameter; repeat for joint dimensions.",
        ),
    ] = None,
    revision: Annotated[
        Path | None, typer.Option(help="Replay and execute a saved permission preview.")
    ] = None,
    format: Annotated[
        OutputFormat, typer.Option("--format", help="auto: text in terminals, JSON in pipes.")
    ] = OutputFormat.AUTO,
    progress: Annotated[
        bool, typer.Option(help="Stream committed progress to stderr; Ctrl+C stops cooperatively.")
    ] = False,
) -> None:
    """Find complete choices without requiring sticky ends or an inline enzyme catalog."""
    with errors(), execution_feedback(progress) as feedback:
        objective = {"kind": "diversity", "parameters": diversify} if diversify else None
        if revision is not None:
            if progress:
                raise ValueError(
                    "Progress requires an exact discovery request, not a staged revision."
                )
            if any(value is not None for value in (request, stem, product, context, left, right)):
                raise ValueError(
                    "A saved revision already binds its intent; omit other request options."
                )
            choices = construction.load_design_revision(revision).execute(
                output,
                max_evaluations=evaluations,
                first_choices=first_choices,
                objective=objective,
            )
        else:
            choices = construction.discover_designs(
                intent(request, stem, product, context, left, right),
                output,
                max_evaluations=evaluations,
                first_choices=first_choices,
                **feedback,
                objective=objective,
            )
        emit_choices(choices, output, format)


@design_app.command("continue")
def continue_search(
    directory: Path,
    evaluations: Annotated[int, typer.Option(min=1)] = 64,
    first_choices: Annotated[int | None, typer.Option(min=1)] = None,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.AUTO,
    progress: Annotated[
        bool, typer.Option(help="Stream committed progress to stderr; Ctrl+C stops cooperatively.")
    ] = False,
) -> None:
    """Explicitly search further under the same saved molecular permissions."""
    with errors(), execution_feedback(progress) as feedback:
        choices = construction.continue_design_discovery(
            directory, max_evaluations=evaluations, first_choices=first_choices, **feedback
        )
        emit_choices(choices, directory, format)


@design_app.command("query")
def query(
    directory: Path,
    *,
    member: Annotated[
        str | None, typer.Option(help="Required stem-family member to inspect.")
    ] = None,
    query: Annotated[
        Path | None, typer.Option(help="Optional filters over recorded choices.")
    ] = None,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.AUTO,
) -> None:
    """Filter existing choices without running a search."""
    with errors():
        emit_choices(load_choices(directory, member), directory, format, query)


@design_app.command("sample")
def sample(
    directory: Path,
    *,
    member: Annotated[
        str | None, typer.Option(help="Required stem-family member to inspect.")
    ] = None,
    seed: Annotated[int | None, typer.Option(min=0)] = None,
    query: Annotated[Path | None, typer.Option()] = None,
    strategy: Annotated[
        str | None, typer.Option(help="preparations, families, or loop (preserve surroundings).")
    ] = None,
    stage: Annotated[
        str | None, typer.Option(help="hairpin or endpoint for guided exploration.")
    ] = None,
    after: Annotated[
        Path | None, typer.Option(help="Previous selection or guided receipt to continue from.")
    ] = None,
    output: Annotated[Path | None, typer.Option("--out", help="New selection JSON file.")] = None,
) -> None:
    """Select one matching recorded preparation with a reproducible seed."""
    with errors():
        previous = json.loads(after.read_bytes()) if after is not None else None
        if previous is not None and not isinstance(previous, dict):
            raise ValueError("Previous selection must be a JSON object.")
        choices = load_choices(directory, member)
        if previous is not None and previous.get("schema", "").startswith("hop.atlas-view/"):
            selected = choices.sample(
                after=previous, seed=seed, query=query, strategy=strategy, stage=stage
            )
            write_selection(selected, output, directory)
            return
        history = ()
        if previous is not None:
            identity = previous.get("selection", previous)["materialized_realization_id"]
            history = (*previous.get("history", ()), identity)
        selected = choices.sample(
            seed=seed,
            query=query if query is not None else previous.get("query") if previous else None,
            strategy=strategy,
            stage=stage or (previous.get("stage", "endpoint") if previous else "endpoint"),
            history=history,
        )
        write_selection(selected, output, directory)


@design_app.command("select")
def select(
    directory: Path,
    *,
    member: Annotated[
        str | None, typer.Option(help="Required stem-family member to inspect.")
    ] = None,
    preparation: Annotated[str, typer.Option(help="Exact preparation identity from a choice.")],
    query: Annotated[Path | None, typer.Option()] = None,
    output: Annotated[Path | None, typer.Option("--out")] = None,
) -> None:
    """Select an exact preparation without copying internal record coordinates."""
    with errors():
        choices = load_choices(directory, member)
        write_selection(choices.select(preparation, query=query), output, directory)


@design_app.command("figure")
def figure(
    directory: Path,
    *,
    member: Annotated[
        str | None, typer.Option(help="Required stem-family member to inspect.")
    ] = None,
    output: Annotated[Path, typer.Option("--out")],
    selection: Annotated[Path | None, typer.Option()] = None,
    query: Annotated[Path | None, typer.Option()] = None,
    view: Annotated[
        str | None, typer.Option(help="parameters, families or similarity; saved view by default.")
    ] = None,
    stage: Annotated[
        str | None, typer.Option(help="hairpin or endpoint for the family view.")
    ] = None,
    layout: Annotated[
        str | None, typer.Option(help="auto, feature_map or mosaic for families.")
    ] = None,
    render_policy: Annotated[
        str | None, typer.Option(help="captured or current molecular artwork.")
    ] = None,
    reference_selection: Annotated[Path | None, typer.Option()] = None,
    axis: Annotated[
        list[str] | None,
        typer.Option(
            "--axis",
            help="Canonical display axis; repeat in drawing order. Does not filter choices.",
        ),
    ] = None,
) -> None:
    """Export the choice landscape and optional selected trace."""
    with errors():
        load_choices(directory, member).figure(
            query=query,
            selection=selection,
            view=view,
            stage=stage,
            layout=layout,
            render_policy=render_policy,
            reference_selection=reference_selection,
            display_axes=None if axis is None else tuple(axis),
        ).write(output)
        typer.echo(output / "figure.pdf")


@design_app.command("atlas")
def atlas(
    directory: Path,
    *,
    member: Annotated[
        str | None, typer.Option(help="Required stem-family member to inspect.")
    ] = None,
    selection: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option("--out")],
    render_policy: Annotated[
        str | None, typer.Option(help="captured or current molecular artwork.")
    ] = None,
    reference_selection: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Replay and export the complete molecular route of the selected preparation."""
    with errors():
        packet = load_choices(directory, member).atlas(
            selection, render_policy=render_policy, reference_selection=reference_selection
        )
        packet.write(output)
        cost = json.loads(packet.json_bytes)["atlas"].get("construction_cost")
        if cost:
            for line in cost["summary_lines"]:
                typer.echo(line)
        typer.echo(output / "projection.svg")


@design_app.command("retrieve")
def retrieve(
    directory: Path,
    *,
    member: Annotated[
        str | None, typer.Option(help="Required stem-family member to inspect.")
    ] = None,
    selection: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option("--out")],
) -> None:
    """Retrieve the exact selected preparation and its oligos."""
    with errors():
        receipt = load_choices(directory, member).retrieve(selection, output)
        emit({"witnesses": list(receipt.materialized_realization_ids)})


@design_app.command("view")
def view(
    directory: Path,
    *,
    member: Annotated[
        str | None, typer.Option(help="Required stem-family member to inspect.")
    ] = None,
    output: Annotated[
        Path, typer.Option("--out", help="New directory for inspected routes and preparations.")
    ],
    port: Annotated[int, typer.Option(min=0, max=65535)] = 0,
    receipt: Annotated[
        Path | None, typer.Option(help="Saved inspection to reopen exactly.")
    ] = None,
) -> None:
    """Open the existing linked choice and molecular views; no search starts implicitly."""
    with errors():
        server = create_design_server(directory, output, port=port, member=member, receipt=receipt)
    typer.echo(f"Design choices: {server.origin}")
    typer.echo("Press Ctrl+C to stop; exports remain in --out.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.session.close()
