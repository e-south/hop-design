"""Apply existing regional controls to complete route facts from an explicit authority."""

from typing import Any

from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.variants.objective import DesignSearchObjective
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..search.diversity import diversity_summary
from .query import molecular_changes, surroundings_reasons


def refine_options(
    result: dict[str, Any],
    query: DesignRefinementQuery,
    options: list[dict[str, Any]],
    *,
    validation: str,
) -> dict[str, Any]:
    reference = next(
        o for o in options if o["label"] == query.reference.materialized_realization_id
    )
    reasons = {
        o["label"]: surroundings_reasons(o, reference, (query.surroundings,)) for o in options
    }
    eligible = {identity for identity, items in reasons.items() if not items}
    for path in result["paths"]:
        path["matches"] = path["matches"] and path["materialized_realization_id"] in eligible
    for axis in result["axes"]:
        for node in axis["nodes"]:
            witnesses = [
                p
                for p in result["paths"]
                if p["materialized_realization_id"] in eligible
                and query.includes_preparation(p["materialized_realization_id"])
                and p["values"].get(axis["key"]) == node["value"]
                and all(
                    s.key == axis["key"] or s.accepts(p["values"].get(s.key))
                    for s in query.parameters
                )
            ]
            node["conditional_records"] = len(witnesses)
            node["conditional_preparations"] = len(
                {p["materialized_realization_id"] for p in witnesses}
            )
            if node["supported_preparations"]:
                node["state"] = "supported" if witnesses else "supported_elsewhere"
    matching = [p for p in result["paths"] if p["matches"]]
    result.update(
        query=query.model_dump(mode="json", by_alias=True),
        query_digest=sha256_digest(canonical_json_bytes(query)),
        matching_records=len(matching),
        matching_preparations=len({p["materialized_realization_id"] for p in matching}),
        matching_products={
            stage: len({p["molecular_identity"][stage] for p in matching})
            for stage in ("hairpin", "endpoint")
        },
        excluded_options=[
            {"label": identity, "reasons": items} for identity, items in reasons.items() if items
        ],
        validation=validation,
        changes=[
            {"label": o["label"], **molecular_changes(o, reference, query.surroundings.stage)}
            for o in options
        ],
    )
    if objective := result.get("search_objective"):
        result["search_objective"] = diversity_summary(
            DesignSearchObjective(kind="diversity", parameters=tuple(objective["parameters"])),
            result["paths"],
        )
    return result
