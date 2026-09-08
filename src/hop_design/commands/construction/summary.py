"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/commands/construction/summary.py

Reports exact construction search accounting and evidence boundaries.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from .common import load_receipt, summary_content


def _count_dispositions(rows: list[dict[str, Any]], status: str) -> int:
    return sum(row["status"] == status for row in rows)


def construction_summary_command(
    bundle_path: Annotated[
        Path,
        typer.Argument(help="Verified HOP construction bundle directory."),
    ],
) -> None:
    """Show the endpoint, search coverage, and route counts."""
    receipt = load_receipt(bundle_path)
    content = summary_content(receipt)
    rows = content["rows"]
    accounting = content["accounting"]
    claims = content["claim_boundary"]
    typer.echo(f"Result: {content['source_result_id']}")
    typer.echo(f"Endpoint: {content['endpoint']}")
    typer.echo(f"Search status: {content['status']}")
    typer.echo(
        f"Combinations: {accounting['examined_combinations']}/"
        f"{accounting['nominal_combinations']} examined"
    )
    typer.echo(
        f"Routes: {_count_dispositions(rows, 'accepted')} accepted · "
        f"{_count_dispositions(rows, 'rejected')} rejected · "
        f"{_count_dispositions(rows, 'truncated')} truncated"
    )
    typer.echo(f"Geometry groups: {len(content['geometry_groups'])}")
    typer.echo(f"Final products: {len(content['final_product_groups'])}")
    method = {
        "resolved_under_declared_molecular_model": ("resolved under the declared molecular model"),
        "not_resolved": "not resolved",
    }[claims["method"]]
    typer.echo(f"Digital method: {method}")
    typer.echo("Physical construction, QC, and biological activity: not recorded")


__all__ = ["construction_summary_command"]
