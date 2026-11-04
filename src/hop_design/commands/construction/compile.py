"""Compose exact selected local authorities using file-oriented public operations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer

from hop_design import construction
from hop_design.api import design_report

from .common import require_output_outside_bundle


def compile_local_design_command(
    design_id: Annotated[str, typer.Option("--design-id")],
    payload: Annotated[str, typer.Option("--payload")],
    endpoint: Annotated[
        Literal["ssdna_hairpin", "hairpin_pcr_duplex", "clone_ready_duplex"],
        typer.Option("--endpoint"),
    ],
    foldback: Annotated[Path, typer.Option("--foldback")],
    foldback_realization_id: Annotated[str, typer.Option("--foldback-realization-id")],
    output: Annotated[Path, typer.Option("--out")],
    basal: Annotated[Path | None, typer.Option("--basal")] = None,
    basal_realization_id: Annotated[str | None, typer.Option("--basal-realization-id")] = None,
    hairpin_left_arm: Annotated[
        str | None,
        typer.Option(
            "--hairpin-left-arm", help="Exact left basal arm, 5'-to-3', for ssdna_hairpin."
        ),
    ] = None,
    hairpin_right_arm: Annotated[
        str | None,
        typer.Option(
            "--hairpin-right-arm", help="Exact right basal arm, 5'-to-3', for ssdna_hairpin."
        ),
    ] = None,
) -> None:
    """Publish one exact design from selected replay-verified local result files."""
    try:
        hairpin_basal_arms = None
        if endpoint == "ssdna_hairpin":
            if hairpin_left_arm is None or hairpin_right_arm is None:
                raise ValueError(
                    "ssdna_hairpin requires both --hairpin-left-arm and --hairpin-right-arm."
                )
            if basal is not None or basal_realization_id is not None:
                raise ValueError("ssdna_hairpin must omit basal discovery selection.")
            hairpin_basal_arms = (hairpin_left_arm, hairpin_right_arm)
        elif hairpin_left_arm is not None or hairpin_right_arm is not None:
            raise ValueError("Hairpin arm options are only for --endpoint ssdna_hairpin.")
        compiled = construction.compile_design_from_local_realizations(
            design_id=design_id,
            payload_sequence=payload,
            endpoint=endpoint,
            foldback=construction.load_verified_local_neighborhood(foldback),
            foldback_realization_id=foldback_realization_id,
            basal=construction.load_verified_local_neighborhood(basal)
            if basal is not None
            else None,
            basal_realization_id=basal_realization_id,
            hairpin_basal_arms=hairpin_basal_arms,
        )
        compiled.write(output)
        typer.echo(design_report(compiled))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def compile_selected_command(
    source: Path,
    design_bundle: Annotated[Path, typer.Option("--design-bundle")],
    foldback: Annotated[Path, typer.Option("--foldback")],
    foldback_realization_id: Annotated[str, typer.Option("--foldback-realization-id")],
    output: Annotated[Path, typer.Option("--out")],
    basal: Annotated[Path | None, typer.Option("--basal")] = None,
    basal_realization_id: Annotated[str | None, typer.Option("--basal-realization-id")] = None,
    source_partition: Annotated[Path | None, typer.Option("--source-partition")] = None,
    source_partition_realization_id: Annotated[
        str | None, typer.Option("--source-partition-realization-id")
    ] = None,
) -> None:
    """Publish one endpoint-complete construction for explicit local selections."""
    try:
        protected_root = require_output_outside_bundle(design_bundle, output)
        compiled = construction.compile_construction_from_local_realizations(
            source,
            design_bundle_path=design_bundle,
            foldback=construction.load_verified_local_neighborhood(foldback),
            foldback_realization_id=foldback_realization_id,
            basal=construction.load_verified_local_neighborhood(basal)
            if basal is not None
            else None,
            basal_realization_id=basal_realization_id,
            source_partition=construction.load_verified_source_partition(source_partition)
            if source_partition is not None
            else None,
            source_partition_realization_id=source_partition_realization_id,
        )
        protected_root.require_unchanged()
        compiled.write(output, protected_root=protected_root)
        typer.echo(compiled.report_json())
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def verify_complete_command(bundle: Path) -> None:
    """Replay every byte and route of a complete construction bundle."""
    try:
        verified = construction.load_verified_construction_bundle(bundle)
        typer.echo(verified.report_json())
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
