"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/commands/construction/selection.py

Inspects exact construction trajectories and persists result-bound references.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

import hop_design.construction as construction

from .common import load_receipt, navigation_content, require_output_outside_bundle


def _resolve_realization_id(
    receipt: construction.VerifiedConstructionBundle,
    *,
    realization_id: str | None,
    selection_path: Path | None,
    ordinal: int | None,
) -> str:
    if sum(value is not None for value in (realization_id, selection_path, ordinal)) != 1:
        raise typer.BadParameter(
            "Provide exactly one route selector.",
            param_hint="route selection",
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


def _external_material_rows(
    realization: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    preparation = realization["source_preparation"]
    rows = [
        ("source_ssdna", preparation["source_ssdna"]),
        ("source_materialization_forward_primer", preparation["forward_primer"]["oligo"]),
        ("source_materialization_reverse_primer", preparation["reverse_primer"]["oligo"]),
    ]
    materials = {item["material_id"]: item for item in realization["materials"]}
    rows.extend(
        (use["role"], materials[use["material_id"]])
        for use in realization["material_uses"]
        if use["route_entry"] == "required_external"
    )
    return rows


def _print_trajectory(content: dict[str, Any]) -> None:
    realization = content["realization"]
    reference = realization["final_product"]["reference"]
    source = realization["source_preparation"]["source_ssdna"]
    materials = _external_material_rows(realization)
    program = realization["construction_program"]
    typer.echo(f"Result: {content['source_result_id']}")
    typer.echo(f"Realization: {realization['materialized_realization_id']}")
    typer.echo(f"Source ssDNA: {source['sequence_5prime']}")
    typer.echo(f"Required external materials: {len(materials)}")
    for role, material in materials:
        typer.echo(
            f"  {role}: {material['sequence_5prime']} · "
            f"5-prime {material['five_prime_end']} · "
            f"3-prime {material['three_prime_end']}"
        )
    typer.echo(
        f"Molecular states: {len(program['states'])} · transitions: {len(program['transitions'])}"
    )
    if content.get("source_partition_certificate") is None:
        typer.echo("Source-fragment removal: unresolved (no bound removal program)")
    else:
        typer.echo("Source-fragment removal: specified and verified in the model")
        typer.echo("Cleanup recovery: not predicted")
    typer.echo(f"Endpoint: {reference['endpoint']} · {reference['topology']}")
    typer.echo(f"Endpoint sequence: {reference['sequence']}")
    if reference["endpoint"] == "clone_ready_duplex":
        for end in realization["final_product"]["cohesive_ends"]:
            typer.echo(
                f"{end['product_end'].capitalize()} cohesive end: {end['sequence']} "
                f"(5-prime to 3-prime) · {end['overhang_end'].replace('_', '-')} overhang"
            )
        typer.echo("Destination compatibility: not evaluated")
    else:
        typer.echo("Cohesive ends: not generated for this endpoint")
    typer.echo("Physical construction, QC, and biological activity: not recorded")


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
) -> None:
    """Inspect the materials and molecular steps of one route."""
    if selection_reason is not None and output is None:
        raise typer.BadParameter("--reason requires --out.", param_hint="--reason")
    receipt = load_receipt(bundle_path)
    if output is not None:
        require_output_outside_bundle(bundle_path, output)
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
        content = json.loads(trajectory.json_bytes)
        if output is not None:
            trajectory.write(output, selection_reason=selection_reason)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="REALIZATION_ID/--out") from exc
    _print_trajectory(content)
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
    receipt = load_receipt(bundle_path)
    require_output_outside_bundle(bundle_path, output)
    selected_id = _resolve_realization_id(
        receipt, realization_id=realization_id, selection_path=None, ordinal=ordinal
    )
    try:
        selected = construction.select_construction_realization(
            receipt,
            materialized_realization_id=selected_id,
        )
        selected.write(output)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="REALIZATION_ID/--out") from exc
    typer.echo(f"Selected reference: {output}")
    typer.echo(f"Result: {selected.source_result_id}")
    typer.echo(f"Realization: {selected.materialized_realization_id}")
    typer.echo("Selection records caller intent; it is not a rank or construction claim.")


__all__ = ["construction_inspect_command", "construction_select_command"]
