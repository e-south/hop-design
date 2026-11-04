"""Incremental interface survey operations, all backed by the file-oriented facade."""

import json
from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction

survey_app = typer.Typer(
    help="Survey complete interface routes with resumable coverage.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


@survey_app.command("evaluate")
def evaluate(
    request: Annotated[Path, typer.Argument(help="Molecular interface survey request.")],
    index: Annotated[Path, typer.Option(help="Create or explicitly resume this SQLite index.")],
    max_evaluations: Annotated[
        int, typer.Option(min=1, help="Maximum committed evaluation steps in this invocation.")
    ],
    local_nodes: Annotated[int, typer.Option(min=1, max=100000)],
    local_realizations: Annotated[int, typer.Option(min=1, max=100000)],
    release_site_pairs: Annotated[int, typer.Option(min=1)],
    continuation_batch_size: Annotated[
        int,
        typer.Option(
            min=1,
            max=1024,
            help="Canonical continuations per commit; stop at a nonempty candidate.",
        ),
    ] = 1,
    navigation_nodes: Annotated[
        int,
        typer.Option(
            min=1, max=100_000, help="Navigation nodes before a resumable seek checkpoint."
        ),
    ] = 256,
    navigation_frontier: Annotated[
        int, typer.Option(min=1, max=100_000, help="Maximum pending completion streams.")
    ] = 4096,
    sequence_decisions: Annotated[int, typer.Option(min=1, max=100_000)] = 100_000,
    sequence_operations: Annotated[int, typer.Option(min=1, max=1_000_000)] = 1_000_000,
    sequence_site_checks: Annotated[int, typer.Option(min=1, max=1_000_000)] = 1_000_000,
    sequence_result_decisions: Annotated[int, typer.Option(min=1, max=1_000_000)] = 1_000_000,
    resume: Annotated[
        bool, typer.Option(help="Continue an existing identically bound index.")
    ] = False,
    max_checkpoint_bytes: Annotated[int, typer.Option(min=1_048_576)] = 1_073_741_824,
) -> None:
    """Evaluate a batch without changing the declared molecular target domain."""
    try:
        result = construction.evaluate_interface_survey(
            request,
            index,
            max_evaluations=max_evaluations,
            local_nodes=local_nodes,
            local_realizations=local_realizations,
            release_site_pairs=release_site_pairs,
            continuation_batch_size=continuation_batch_size,
            navigation_nodes=navigation_nodes,
            navigation_frontier=navigation_frontier,
            sequence_decisions=sequence_decisions,
            sequence_operations=sequence_operations,
            sequence_site_checks=sequence_site_checks,
            sequence_result_decisions=sequence_result_decisions,
            resume=resume,
            max_checkpoint_bytes=max_checkpoint_bytes,
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, sort_keys=True))


@survey_app.command("inspect")
def inspect(
    request: Path,
    index: Annotated[Path, typer.Option()],
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
) -> None:
    """List recorded evaluations and witness addresses without generating drawings."""
    try:
        result = construction.inspect_interface_survey(request, index, offset=offset, limit=limit)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, sort_keys=True))


@survey_app.command("verify")
def verify(request: Path, index: Annotated[Path, typer.Option()]) -> None:
    """Replay every recorded evaluation before using aggregate coverage as evidence."""
    try:
        result = construction.verify_interface_survey(request, index)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, sort_keys=True))


@survey_app.command("query")
def query_choices(
    request: Path,
    index: Annotated[Path, typer.Option()],
    query: Annotated[Path | None, typer.Option(help="Optional typed parameter predicates.")] = None,
    output: Annotated[
        Path | None, typer.Option("--out", help="New portable figure directory.")
    ] = None,
    selection: Annotated[
        Path | None, typer.Option(help="Exact selection to highlight in the figure.")
    ] = None,
) -> None:
    """Read conditional complete paths and declared values without extending the search."""
    try:
        if output is not None:
            packet = construction.load_interface_survey_choices(request, index).figure(
                query, selection=selection
            )
            packet.write(output)
            typer.echo(packet.json_bytes.decode())
            return
        if selection is not None:
            raise ValueError("--selection requires --out for a selected figure.")
        result = construction.query_interface_survey(request, index, query)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, sort_keys=True))


@survey_app.command("select")
def select(
    request: Path,
    index: Annotated[Path, typer.Option()],
    target: Annotated[int, typer.Option(min=0)],
    step: Annotated[int, typer.Option(min=0)],
    identity: Annotated[str, typer.Option(help="Exact preparation identity from the query path.")],
    query: Annotated[Path | None, typer.Option(help="Typed predicates to preserve.")] = None,
) -> None:
    """Emit one exact query-bound selection for atlas and retrieval."""
    try:
        pool = construction.load_interface_survey_choices(request, index)
        selected = pool.select(
            target=target, step=step, materialized_realization_id=identity, query=query
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(selected, sort_keys=True))


@survey_app.command("sample")
def sample(
    request: Path,
    index: Annotated[Path, typer.Option()],
    seed: Annotated[int, typer.Option(min=0)],
    query: Annotated[Path | None, typer.Option(help="Typed predicates to preserve.")] = None,
) -> None:
    """Emit a seeded selection among matching exact preparations, without new search."""
    try:
        selected = construction.load_interface_survey_choices(request, index).sample(
            seed=seed, query=query
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(selected, sort_keys=True))


@survey_app.command("retrieve")
def retrieve(
    request: Path,
    index: Annotated[Path, typer.Option()],
    selection: Annotated[Path, typer.Option(help="Exact query-bound selection JSON.")],
    output: Annotated[Path, typer.Option("--out", help="New selected preparation directory.")],
) -> None:
    """Replay the selected witness and export its exact preparation and molecular trace."""
    try:
        receipt = construction.retrieve_interface_survey_witness(
            request,
            index,
            selection=selection,
            destination=output,
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(
        json.dumps({"witnesses": list(receipt.materialized_realization_ids)}, sort_keys=True)
    )


@survey_app.command("atlas")
def atlas(
    request: Path,
    index: Annotated[Path, typer.Option()],
    selection: Annotated[Path, typer.Option(help="Exact query-bound selection JSON.")],
    output: Annotated[Path, typer.Option("--out", help="New atlas projection directory.")],
    reference_selection: Annotated[
        Path | None, typer.Option(help="Exact reference selection JSON for comparison.")
    ] = None,
) -> None:
    """Replay the selected path and draw its nucleotide-resolution construction atlas."""
    try:
        packet = construction.inspect_interface_survey_atlas(
            request, index, selection=selection, reference_selection=reference_selection
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(packet.json_bytes.decode())


@survey_app.command("view")
def view(
    request: Path,
    index: Annotated[Path, typer.Option()],
    output: Annotated[
        Path, typer.Option("--out", help="New directory for inspected atlases and preparations.")
    ],
    port: Annotated[int, typer.Option(min=0, max=65535)] = 0,
) -> None:
    """Browse conditional complete paths locally; no implicit search or relaxation."""
    from ..editor.server import create_survey_server

    try:
        server = create_survey_server(request, index, output, port=port)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"Interface survey: {server.origin}")
    typer.echo("Press Ctrl+C to stop; generated atlases and preparations remain in --out.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.session.close()
