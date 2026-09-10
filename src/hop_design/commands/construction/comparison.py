"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/commands/construction/comparison.py

Prints molecular differences between selected routes in two verified bundles.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

import hop_design.construction as construction

from .common import load_receipt
from .selection import _resolve_realization_id


def construction_compare_command(
    left_bundle: Annotated[
        Path, typer.Argument(help="Verified construction bundle for the left route.")
    ],
    right_bundle: Annotated[
        Path, typer.Argument(help="Verified construction bundle for the right route.")
    ],
    left_ordinal: Annotated[
        int, typer.Option("--left-ordinal", help="Left route number from construction list.")
    ],
    right_ordinal: Annotated[
        int, typer.Option("--right-ordinal", help="Right route number from construction list.")
    ],
) -> None:
    """Compare selected oligos, processing, retained sequence, and actual products."""
    left = load_receipt(left_bundle)
    right = left if left_bundle.resolve() == right_bundle.resolve() else load_receipt(right_bundle)
    left_id = _resolve_realization_id(
        left, realization_id=None, selection_path=None, ordinal=left_ordinal
    )
    right_id = _resolve_realization_id(
        right, realization_id=None, selection_path=None, ordinal=right_ordinal
    )
    try:
        report = construction.compare_constructions(
            left, right, left_realization_id=left_id, right_realization_id=right_id
        )
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="route selection") from exc
    typer.echo(report, nl=False)
