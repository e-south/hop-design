"""Preview explicit molecular permission revisions without launching a search."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction

from .common import errors
from .presentation import OutputFormat, use_text


def register_permission_commands(app: typer.Typer) -> None:
    @app.command("revise")
    def revise(
        changes: Annotated[Path, typer.Option(help="Small permission-revision JSON or YAML.")],
        output: Annotated[
            Path, typer.Option("--out", help="New preview packet; no search starts.")
        ],
        directory: Annotated[Path | None, typer.Argument(help="Existing design choices.")] = None,
        request: Annotated[
            Path | None, typer.Option(help="Intent to revise before discovery.")
        ] = None,
        format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.AUTO,
    ) -> None:
        """Preview permission changes and their dependencies while preserving intent."""
        with errors():
            if (directory is None) == (request is None):
                raise ValueError("Provide existing design choices or --request, not both.")
            if request is not None:
                preview = construction.preview_design_revision(request, changes)
            else:
                assert directory is not None
                preview = construction.load_design_choices(directory).revise(changes)
            preview.write(output)
            if use_text(format):
                typer.echo(preview.report_text)
                typer.echo(f"Saved permission preview: {output}")
            else:
                typer.echo(preview.json_bytes.decode())
