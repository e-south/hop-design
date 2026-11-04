"""Capture frozen editions without introducing another search entry point."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design.construction import freeze_design_choices

from .common import emit, errors, load_choices


def register_edition_commands(app: typer.Typer) -> None:
    @app.command("neighbors")
    def neighbors(
        directory: Path,
        preparation: Annotated[str, typer.Option(help="Reference preparation identity.")],
        query: Annotated[Path | None, typer.Option()] = None,
        limit: Annotated[int, typer.Option(min=1, max=32)] = 5,
        verify_controls: Annotated[
            bool, typer.Option(help="Verify preservation for returned neighbors.")
        ] = True,
        timeout_seconds: Annotated[float, typer.Option(min=0.001, max=300)] = 5.0,
    ) -> None:
        """Explain molecular neighbors within the active recorded choices."""
        with errors():
            emit(
                load_choices(directory).neighbors(
                    preparation,
                    query=query,
                    limit=limit,
                    verify_controls=verify_controls,
                    timeout_seconds=timeout_seconds,
                )
            )

    @app.command("preview")
    def preview(
        directory: Path,
        preparation: Annotated[str, typer.Option(help="Exact recorded preparation identity.")],
        output: Annotated[Path, typer.Option("--out")],
        query: Annotated[Path | None, typer.Option(help="Eligibility filters; no search.")] = None,
    ) -> None:
        """Inspect one exact hairpin and parameter trace without committing a selection."""
        with errors():
            packet = load_choices(directory).preview(preparation, query=query)
            packet.write(output)
            typer.echo(output / "overview.svg")

    @app.command("freeze")
    def freeze(
        directory: Path,
        output: Annotated[Path, typer.Option("--out")],
        query: Annotated[Path | None, typer.Option(help="Optional filter to capture.")] = None,
        identity: Annotated[
            list[str] | None, typer.Option(help="Preparation to include; repeat for several.")
        ] = None,
        include_landscape: Annotated[
            bool, typer.Option(help="Capture fixed molecular-similarity coordinates.")
        ] = False,
        compact: Annotated[
            bool, typer.Option(help="Store exact authorities compactly; draw on selection.")
        ] = False,
        distance_policy: Annotated[
            Path | None,
            typer.Option(help="Explicit molecular-distance JSON; requires --include-landscape."),
        ] = None,
        comparison_weights: Annotated[
            tuple[float, float, float] | None,
            typer.Option(
                help="Geometry, sequence and interface weights; requires --include-landscape."
            ),
        ] = None,
        source_contract: Annotated[
            Path | None,
            typer.Option(
                help="Explicit recorded producer and input bindings; compact capture only."
            ),
        ] = None,
    ) -> None:
        """Freeze recorded choices, exact molecular views and materials for portable inspection."""
        with errors():
            edition = freeze_design_choices(
                directory,
                output,
                query=query,
                identities=tuple(identity) if identity else None,
                include_landscape=include_landscape,
                compact=compact,
                distance_policy=distance_policy,
                comparison_weights=comparison_weights,
                source_contract=source_contract,
            )
            emit(
                {
                    "edition_digest": edition.digest,
                    "preparations": edition.query()["matching_preparations"],
                }
            )

    @app.command("parameters")
    def parameters(
        directory: Path,
        query: Annotated[
            Path | None, typer.Option(help="Explain active constraints without searching.")
        ] = None,
        member: Annotated[
            str | None, typer.Option(help="Exact member of a required stem family.")
        ] = None,
    ) -> None:
        """Describe molecular parameters, constraints and supported operations."""
        with errors():
            emit(load_choices(directory, member).parameters(query=query))
