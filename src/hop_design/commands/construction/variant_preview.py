"""Preview supported local choices through the same public operation as the viewport."""

import json
from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def preview_variant_command(
    options: Annotated[Path, typer.Argument(help="Verified discovery or molecular edit result.")],
    choices: Annotated[Path, typer.Argument(help="Saved conditional choices packet.")],
    variant: Annotated[
        str, typer.Option(help="Observed variant identity in the focused neighborhood.")
    ],
    output: Annotated[Path, typer.Option("--out", help="New preview packet directory.")],
    state: Annotated[
        str, typer.Option(help="All processing steps, a phase, role or exact recorded state ID.")
    ] = "all",
    option: Annotated[
        str | None, typer.Option(help="Explicit preparation when choices remain.")
    ] = None,
    focus: Annotated[Path | None, typer.Option(help="Saved inspected address JSON.")] = None,
    focus_option: Annotated[
        str | None, typer.Option(help="Preparation owning the inspected address.")
    ] = None,
    focus_mode: Annotated[
        str, typer.Option(help="Position transfer: material ancestry or verified comparison.")
    ] = "material",
    view_from: Annotated[
        Path | None, typer.Option(help="Previous view JSON: option_label and recorded state.")
    ] = None,
) -> None:
    """Preview without editing permissions, requiring members or selecting a preparation."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        pool = construction.load_scaffold_exploration(options)
        admitted = construction.load_scaffold_variant_choices(pool, choices)
        packet = construction.preview_scaffold_variant(
            pool,
            admitted,
            {
                "result_digest": pool.result_digest,
                "query_digest": json.loads(admitted.json_bytes)["query_digest"],
                "variant_id": variant,
                "state": state,
                "option_label": option,
                "focus": json.loads(focus.read_bytes()) if focus else None,
                "focus_option_label": focus_option,
                "focus_mode": focus_mode,
                "view_from": json.loads(view_from.read_bytes()) if view_from else None,
            },
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/CHOICES/preview/--out") from error
    typer.echo(packet.report_text)
