"""Export a selected whole-hairpin portrait together with its exact preparation."""

from pathlib import Path
from typing import Annotated

import typer

import hop_design.construction as construction

from .common import load_receipt, require_output_outside_bundle
from .selection import _resolve_realization_id, _validate_route_selector


def construction_portrait_command(
    bundle_path: Annotated[Path, typer.Argument(help="Verified complete construction bundle.")],
    output: Annotated[Path, typer.Option("--out", help="New portrait and preparation directory.")],
    realization_id: Annotated[
        str | None, typer.Argument(help="Exact accepted realization identity.")
    ] = None,
    selection_path: Annotated[
        Path | None, typer.Option("--selection", help="Result-bound selection JSON.")
    ] = None,
) -> None:
    """See one whole hairpin, then retrieve the preparation for that exact choice."""
    _validate_route_selector(
        realization_id=realization_id, selection_path=selection_path, ordinal=None
    )
    protected_root = require_output_outside_bundle(bundle_path, output)
    receipt = load_receipt(bundle_path, protected_root=protected_root)
    selected = _resolve_realization_id(
        receipt, realization_id=realization_id, selection_path=selection_path, ordinal=None
    )
    try:
        portrait = construction.project_hairpin_portrait(
            receipt, materialized_realization_id=selected
        )
        portrait.write(output, protected_root=protected_root)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="REALIZATION_ID/--out") from exc
    typer.echo(f"Hairpin: {output / 'projection.svg'}")
    typer.echo(f"Exact preparation: {output / 'preparation/oligos.csv'}")
    typer.echo(f"Selection: {output / 'selection.json'}")


__all__ = ["construction_portrait_command"]
