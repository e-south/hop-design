"""One complete-outcome summary shared by execution and saved-report admission."""

import json
from typing import Any

from hop_design.serialization import canonical_json_bytes

from ..public import (
    ConstructionCompilation,
    VerifiedConstructionBundle,
    project_complete_construction_summary,
)
from .site_conflicts import actionable_site_conflicts


def describe_complete_outcome(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> dict[str, Any]:
    rows = json.loads(project_complete_construction_summary(receipt).json_bytes)["rows"]
    constraints = {
        canonical_json_bytes(r["preparation_constraint"]): r["preparation_constraint"]
        for r in rows
        if r.get("preparation_constraint") is not None
    }
    values = {
        "preparation_constraints": [constraints[key] for key in sorted(constraints)],
        "stage": "construction",
        "scope": "selected_combination",
        "status": receipt.status,
        "result_id": receipt.result_id,
        "accepted": len(receipt.materialized_realization_ids),
        "rejection_reasons": sorted({r["rejection_reason"] for r in rows if r["rejection_reason"]}),
    }
    mismatches = [m for row in rows for m in row.get("scaffold_mismatches", [])]
    if mismatches:
        values["scaffold_mismatches"] = mismatches
    sites = actionable_site_conflicts(receipt)
    if sites:
        values["actionable_site_conflicts"] = sites
    return values
