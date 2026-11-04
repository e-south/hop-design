"""Project an edited request's complete options and preserve native coverage semantics."""

from typing import Any


def edit_result_summary(preview: dict[str, Any], discovery: dict[str, Any]) -> dict[str, Any]:
    placements = next(
        (c["after"] for c in preview["changes"] if c["field"] == "end_placements"), None
    )
    complete = [
        o["target_facts"]["end_placement"]
        for o in discovery["options"]
        if o.get("target_facts", {}).get("end_placement") is not None
    ]
    # Joint distances form a partial order: expose all nondominated examined pairs.
    frontier = [
        p
        for p in complete
        if not any(
            q != p and q["left_bp"] <= p["left_bp"] and q["right_bp"] <= p["right_bp"]
            for q in complete
        )
    ]
    frontier = list({(p["left_bp"], p["right_bp"]): p for p in frontier}.values())
    return {
        "schema": "hop.molecular-edit-result/v1",
        "edit_digest": preview["edit_digest"],
        "original_request_digest": preview["original_request_digest"],
        "changes": preview["changes"],
        "producer": discovery["producer"],
        "endpoint": discovery["endpoint"],
        "comparison_stage": discovery["comparison_stage"],
        "coverage": discovery["coverage"],
        "search_schedule": discovery.get("search_schedule"),
        "branches": [
            {
                **branch,
                "report": "options/" + branch["report"],
                "request": "options/" + branch["request"],
                "failures": [
                    {**failure, "outcome": "options/" + failure["outcome"]}
                    for failure in branch["failures"]
                ],
            }
            for branch in discovery["branches"]
        ],
        "options": [
            {
                **o,
                "selection": {k: "options/" + v for k, v in o["selection"].items()},
                **{
                    key: "options/" + o[key]
                    for key in ("portrait", "closing_drawing", "product_stages", "preparation")
                },
                "sequence_view": f"views/{o['label']}.json",
                "sequence_drawing": f"views/{o['label']}.svg",
            }
            for o in discovery["options"]
        ],
        "selected_options": [],
        "display_reference": discovery["options"][0]["label"] if discovery["options"] else None,
        "display_reference_policy": (
            "first recorded option for highlighting only; not selected or ranked"
        ),
        **(
            {
                "end_placement_comparison": {
                    "requested": placements,
                    "closest_complete_examined": frontier[0] if len(frontier) == 1 else None,
                    "nondominated_complete_examined": frontier,
                    "global_minimum": "not_assessed",
                }
            }
            if placements is not None
            else {}
        ),
    }
