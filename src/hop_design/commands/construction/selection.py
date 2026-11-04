"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/commands/construction/selection.py

Inspects exact construction trajectories and persists result-bound references.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

import hop_design.construction as construction

from .common import load_receipt, navigation_content, require_output_outside_bundle


def _validate_route_selector(
    *, realization_id: str | None, selection_path: Path | None, ordinal: int | None
) -> None:
    if sum(value is not None for value in (realization_id, selection_path, ordinal)) != 1:
        raise typer.BadParameter(
            "Provide exactly one route selector.", param_hint="route selection"
        )
    if ordinal is not None and ordinal < 0:
        raise typer.BadParameter("Route ordinal must be nonnegative.", param_hint="--ordinal")


def _resolve_realization_id(
    receipt: construction.VerifiedConstructionBundle,
    *,
    realization_id: str | None,
    selection_path: Path | None,
    ordinal: int | None,
) -> str:
    _validate_route_selector(
        realization_id=realization_id, selection_path=selection_path, ordinal=ordinal
    )
    if ordinal is not None:
        for row in navigation_content(receipt)["rows"]:
            if row["ordinal"] == ordinal and row["status"] == "accepted":
                return str(row["materialized_realization_id"])
        raise typer.BadParameter(
            f"No accepted route has ordinal {ordinal}. "
            "Use construction list to see available routes.",
            param_hint="--ordinal",
        )
    if selection_path is not None:
        try:
            selected = construction.load_construction_selection(
                selection_path,
                receipt=receipt,
            )
        except (OSError, ValueError) as exc:
            raise typer.BadParameter(str(exc), param_hint="--selection") from exc
        return selected.materialized_realization_id
    assert realization_id is not None
    if realization_id not in receipt.materialized_realization_ids:
        raise typer.BadParameter(
            f"Unknown accepted construction realization: {realization_id}",
            param_hint="REALIZATION_ID",
        )
    return realization_id


def construction_inspect_command(
    bundle_path: Annotated[
        Path,
        typer.Argument(help="Verified HOP construction bundle directory."),
    ],
    realization_id: Annotated[
        str | None,
        typer.Argument(help="Accepted materialized realization identity."),
    ] = None,
    selection_path: Annotated[
        Path | None,
        typer.Option("--selection", help="Result-bound construction selection JSON."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--out", help="New directory for the report, oligos, and exact route details."
        ),
    ] = None,
    ordinal: Annotated[
        int | None,
        typer.Option("--ordinal", help="Route number from construction list for this same bundle."),
    ] = None,
    selection_reason: Annotated[
        str | None,
        typer.Option("--reason", help="Your reason for selecting this route, saved with --out."),
    ] = None,
    product_end: Annotated[
        str | None,
        typer.Option(
            "--end", help="Focus on the recorded origins of the left or right released end."
        ),
    ] = None,
    base_index: Annotated[
        int | None,
        typer.Option(
            "--base-index", help="Zero-based position in the --end word, read 5-prime first."
        ),
    ] = None,
) -> None:
    """Inspect the materials and molecular steps of one route."""
    if selection_reason is not None and output is None:
        raise typer.BadParameter("--reason requires --out.", param_hint="--reason")
    if base_index is not None and product_end is None:
        raise typer.BadParameter("--base-index requires --end.", param_hint="--base-index")
    if product_end is not None and product_end not in {"left", "right"}:
        raise typer.BadParameter("--end must be left or right.", param_hint="--end")
    if base_index is not None and base_index < 0:
        raise typer.BadParameter("Base index must be nonnegative.", param_hint="--base-index")
    _validate_route_selector(
        realization_id=realization_id, selection_path=selection_path, ordinal=ordinal
    )
    protected_root = None if output is None else require_output_outside_bundle(bundle_path, output)
    receipt = load_receipt(bundle_path, protected_root=protected_root)
    selected_id = _resolve_realization_id(
        receipt,
        realization_id=realization_id,
        selection_path=selection_path,
        ordinal=ordinal,
    )
    try:
        trajectory = construction.project_construction_trajectory(
            receipt,
            materialized_realization_id=selected_id,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="REALIZATION_ID") from exc
    try:
        inspection = (
            trajectory.inspection_text
            if product_end is None
            else trajectory.inspect_end(product_end, base_index=base_index)
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--end/--base-index") from exc
    try:
        if output is not None:
            trajectory.write(
                output, selection_reason=selection_reason, protected_root=protected_root
            )
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="--out") from exc
    typer.echo(inspection)
    if output is not None:
        typer.echo(f"Report: {output / 'report.md'}")
        typer.echo(f"Oligos: {output / 'oligos.csv'} · {output / 'oligos.fasta'}")


def construction_select_command(
    bundle_path: Annotated[
        Path,
        typer.Argument(help="Verified HOP construction bundle directory."),
    ],
    output: Annotated[
        Path,
        typer.Option("--out", help="New JSON file for the result-bound reference."),
    ],
    realization_id: Annotated[
        str | None,
        typer.Argument(help="Accepted materialized realization identity."),
    ] = None,
    ordinal: Annotated[
        int | None,
        typer.Option("--ordinal", help="Route number from construction list for this same bundle."),
    ] = None,
) -> None:
    """Save a selection referencing an existing route."""
    _validate_route_selector(realization_id=realization_id, selection_path=None, ordinal=ordinal)
    protected_root = require_output_outside_bundle(bundle_path, output)
    receipt = load_receipt(bundle_path, protected_root=protected_root)
    selected_id = _resolve_realization_id(
        receipt, realization_id=realization_id, selection_path=None, ordinal=ordinal
    )
    try:
        selected = construction.select_construction_realization(
            receipt,
            materialized_realization_id=selected_id,
        )
        selected.write(output, protected_root=protected_root)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="REALIZATION_ID/--out") from exc
    typer.echo(f"Selected reference: {output}")
    typer.echo(f"Result: {selected.source_result_id}")
    typer.echo(f"Realization: {selected.materialized_realization_id}")
    typer.echo("Selection records caller intent; it is not a rank or construction claim.")


__all__ = ["construction_inspect_command", "construction_select_command"]
