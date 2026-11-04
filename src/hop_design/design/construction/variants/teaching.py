"""Assemble one teaching view after complete preparation and query admission."""

import json
from typing import Any

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.projections.atlas import MolecularAtlas

from ..projections.parameter_locations import parameter_locations
from ..projections.parameter_teaching import parameter_teaching
from .public import ScaffoldExploration


def teaching_view(
    pool: ScaffoldExploration,
    summary: dict[str, Any],
    label: str,
    route: MaterializedConstructionRealization,
    atlas: MolecularAtlas,
    envelope: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = next(p for p in summary["choice_space"]["paths"] if p["option_label"] == label)
    locations = parameter_locations(route, atlas, path["values"])
    request = json.loads(pool._request)
    context = {
        "material_policies": request["product"]["materialization"],
        "permitted_preparation_changes": request["preparation_changes"],
        "preservation": envelope["preserved"],
        "end_placements": envelope["end_placements"],
        **(
            {"receiving_end_pairs": envelope["receiving_end_pairs"]}
            if "receiving_end_pairs" in envelope
            else {}
        ),
        "coverage": envelope["coverage"],
        "budgets": {
            "max_branches": request["max_branches"],
            "max_continuations_per_branch": request["max_continuations_per_branch"],
            "foldback": request["product"]["foldback"]["search"],
            "basal": (request["product"].get("basal") or {}).get("search"),
        },
    }
    teaching = parameter_teaching(
        route,
        atlas,
        locations,
        path["values"],
        summary["choice_space"]["axes"],
        context,
    )
    return teaching, locations
