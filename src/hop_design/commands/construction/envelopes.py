"""Thin file-oriented adapters for explicit construction-envelope revisions."""

from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def parameter_values_command(
    options: Annotated[Path, typer.Argument(help="Verified exploration directory.")],
    choices: Annotated[Path, typer.Argument(help="Saved query and preservation controls.")],
    parameter: Annotated[str, typer.Option(help="Molecular parameter key.")],
    output: Annotated[Path, typer.Option("--out", help="New domain-page directory.")],
    length: Annotated[
        int | None, typer.Option(help="Loop length for an unfixed word domain.")
    ] = None,
    prefix: Annotated[str, typer.Option(help="Exact A/C/G/T prefix for sequence navigation.")] = "",
    offset: Annotated[int, typer.Option(min=0)] = 0,
    limit: Annotated[int, typer.Option(min=1, max=64)] = 32,
) -> None:
    """List permitted coordinates even when no completed preparation uses them."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        pool = construction.load_scaffold_exploration(options)
        query = construction.load_scaffold_variant_choices(pool, choices)
        page = construction.query_scaffold_parameter_domain(
            pool,
            query,
            {
                "key": parameter,
                "length": length,
                "prefix": prefix,
                "offset": offset,
                "limit": limit,
            },
        )
        page.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/CHOICES/parameter/page") from error
    typer.echo(page.json_bytes.decode())


def revise_envelope_command(
    options: Annotated[Path, typer.Argument(help="Verified exploration directory.")],
    choices: Annotated[Path, typer.Argument(help="Saved query and preservation controls.")],
    revision: Annotated[Path, typer.Argument(help="Explicit envelope field revisions.")],
    output: Annotated[Path, typer.Option("--out", help="New preview directory.")],
) -> None:
    """Preview changed generating permissions without evaluating constructions."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        pool = construction.load_scaffold_exploration(options)
        query = construction.load_scaffold_variant_choices(pool, choices)
        preview = construction.preview_scaffold_envelope_revision(pool, query, revision)
        preview.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/CHOICES/REVISION/--out") from error
    typer.echo(preview.report_text)


def evaluate_envelope_command(
    options: Annotated[Path, typer.Argument(help="Original verified exploration directory.")],
    preview: Annotated[Path, typer.Argument(help="Saved explicit envelope revision preview.")],
    output: Annotated[Path, typer.Option("--out", help="New extended exploration directory.")],
    max_branches: Annotated[int, typer.Option(min=1, max=64)],
    max_continuations: Annotated[int, typer.Option(min=1, max=64)],
) -> None:
    """Evaluate a previewed envelope under explicit computation bounds."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        pool = construction.load_scaffold_exploration(options)
        revision = construction.load_scaffold_envelope_revision(pool, preview)
        result = construction.evaluate_scaffold_envelope_revision(
            pool,
            revision,
            max_branches=max_branches,
            max_continuations_per_branch=max_continuations,
        )
        result.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/PREVIEW/bounds/--out") from error
    typer.echo(result.report_text)
