"""Project transport facts without duplicating the exact molecular authority."""

from hop_design.models.construction.variants.inspection_summary import InspectionSummary
from hop_design.serialization import canonical_json_bytes

from .types import Record


def _description(comparison: Record, selection: Record) -> str | None:
    before, after = comparison["reference_loop"], comparison["observed_loop"]
    if before == after:
        return None
    query = selection.get("query", {})
    held = (
        query.get("surroundings") == {"stage": "hairpin", "except_neighborhood": "loop"}
        and query.get("reference", {}).get("materialized_realization_id") == comparison["reference"]
    )
    return f"Loop {before} → {after}" + ("; other hairpin regions held." if held else ".")


def inspection_summary(summary: Record, selection: Record) -> Record:
    atlas, comparison = summary["atlas"], summary.get("comparison")
    projected = {
        "selection": selection,
        "rendering": summary.get("rendering"),
        "atlas": {
            "materialized_realization_id": atlas["materialized_realization_id"],
            "states": [
                {"state": {k: s["state"][k] for k in ("state_id", "phase")}}
                for s in atlas["states"]
            ],
            "construction_cost": atlas.get("construction_cost"),
        },
        "comparison": None
        if comparison is None
        else {
            "description": _description(comparison, selection),
            **{
                k: comparison[k]
                for k in (
                    "reference",
                    "notices",
                    "reference_loop",
                    "observed_loop",
                    "material_roles",
                )
            },
            "transitions": [
                {"links": [{k: link[k] for k in ("reference", "target")} for link in t["links"]]}
                for t in comparison["transitions"]
            ],
        },
    }
    return InspectionSummary.model_validate_json(canonical_json_bytes(projected)).model_dump(
        mode="json", by_alias=True
    )
