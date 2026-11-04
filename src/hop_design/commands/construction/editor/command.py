"""Start an explicitly local molecular editor; never bind a public network interface."""

from pathlib import Path
from typing import Annotated

import typer

from .server import create_editor_server


def edit_view_command(
    request: Annotated[Path, typer.Argument(help="Original scaffold discovery request.")],
    output: Annotated[
        Path, typer.Option("--out", help="New directory for explicit edits and preparations.")
    ],
    port: Annotated[
        int, typer.Option(min=0, max=65535, help="Loopback port; 0 chooses a free port.")
    ] = 0,
    evaluated: Annotated[
        bool,
        typer.Option(help="Browse a verified result packet; no new search or authored inputs."),
    ] = False,
) -> None:
    """Edit a folded sequence locally, evaluate complete alternatives and retrieve preparations."""
    try:
        server = create_editor_server(request, output, port=port, evaluated=evaluated)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="REQUEST/--out/--port") from error
    typer.echo(f"Molecular editor: {server.origin}")
    typer.echo("Press Ctrl+C to stop; generated preparations remain in --out.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.session.close()
