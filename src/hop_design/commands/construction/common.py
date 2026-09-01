"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/commands/construction/common.py

Loads verified construction receipts and their public summary projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

import hop_design.construction as construction


def load_receipt(path: Path) -> construction.VerifiedConstructionBundle:
    """Load a construction authority and translate expected CLI failures."""
    try:
        return construction.load_verified_construction_bundle(path)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="BUNDLE_PATH") from exc


def require_output_outside_bundle(bundle_path: Path, output_path: Path) -> None:
    """Keep non-authoritative exports outside the verified input authority."""
    bundle_root = bundle_path.resolve(strict=True)
    destination = output_path.resolve(strict=False)
    if destination == bundle_root or destination.is_relative_to(bundle_root):
        raise typer.BadParameter(
            "--out must be outside the verified construction bundle.",
            param_hint="--out",
        )


def summary_content(
    receipt: construction.VerifiedConstructionBundle,
) -> dict[str, Any]:
    """Return the public replay-derived summary relation as structured data."""
    packet = construction.project_complete_construction_summary(receipt)
    content = json.loads(packet.json_bytes)
    if not isinstance(content, dict):  # pragma: no cover - projection contract protects this
        raise ValueError("Construction summary projection root must be a mapping.")
    return content


def navigation_content(
    receipt: construction.VerifiedConstructionBundle,
) -> dict[str, Any]:
    """Join the accepted-route overlay to its exact summary for CLI navigation."""
    packet = construction.project_construction_navigation(receipt)
    content = json.loads(packet.json_bytes)
    if not isinstance(content, dict):  # pragma: no cover - projection contract protects this
        raise ValueError("Construction navigation projection root must be a mapping.")
    summary = content["summary"]
    routes = {route["materialized_realization_id"]: route for route in content["accepted_routes"]}
    rows = []
    for summary_row in summary["rows"]:
        realization_id = summary_row["materialized_realization_id"]
        route = None if realization_id is None else routes[realization_id]
        material_ids = summary_row["material_ids"]
        rows.append(
            {
                **summary_row,
                "foldback_geometry": None if route is None else route["foldback_geometry"],
                "basal_geometry": None if route is None else route["basal_geometry"],
                "foldback_relaxation_radius": (
                    None if route is None else route["foldback_relaxation_radius"]
                ),
                "basal_relaxation_radius": (
                    None if route is None else route["basal_relaxation_radius"]
                ),
                "exact_geometry": None if route is None else route["exact_geometry"],
                "enzyme_ids": () if route is None else route["cleavage_enzyme_ids"],
                "enzyme_count": 0 if route is None else len(route["cleavage_enzyme_ids"]),
                "retained_non_payload_nt": (
                    0 if route is None else route["retained_non_payload_nt"]
                ),
                "required_external_material_count": len(material_ids),
                "auxiliary_material_count": max(0, len(material_ids) - 1),
                "final_product_id": (
                    None if route is None else summary_row["final_product_group_key"]
                ),
                "final_product_topology": (
                    None if route is None else route["final_product_topology"]
                ),
            }
        )
    return {
        **summary,
        "rows": rows,
        "geometry_groups": content["geometry_groups"],
        "navigation_projection_id": content["projection_id"],
    }


__all__ = [
    "load_receipt",
    "navigation_content",
    "require_output_outside_bundle",
    "summary_content",
]
