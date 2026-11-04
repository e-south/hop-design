"""Project bounded branch outcomes without inventing product or failure facts."""

import json
from pathlib import Path
from typing import Any

from ..public import VerifiedConstructionBundle
from .molecules import molecular_identities, preparation_materials, stage_groups
from .parameter_admission import candidate_parameter_reasons


def branch_record(
    root: Path,
    branch: dict[str, Any],
    result: dict[str, Any],
    ordinal: int,
    receipts: dict[str, VerifiedConstructionBundle],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    prefix = f"branches/{ordinal:04d}"
    failures = []
    for candidate in result["candidates"]:
        if candidate["status"] == "complete":
            continue
        outcome_path = Path(candidate["outcome"]).with_name("summary.json")
        outcome = json.loads((root / prefix / outcome_path).read_bytes())
        failures.append(
            {
                "outcome": f"{prefix}/{candidate['outcome']}",
                **{
                    key: outcome.get(key, [])
                    for key in (
                        "rejection_reasons",
                        "preparation_constraints",
                        "scaffold_mismatches",
                    )
                },
                "scope": outcome["scope"],
                "status": outcome["status"],
                **(
                    {"actionable_site_conflicts": outcome["actionable_site_conflicts"]}
                    if outcome.get("actionable_site_conflicts")
                    else {}
                ),
            }
        )
    options = []
    parameter_exclusions = []
    for option in result["options"]:
        receipt = receipts[option["label"]]
        if branch.get("parameter_constraints"):
            route = next(
                r
                for r in receipt._verified_source().result.realizations
                if r.materialized_realization_id == option["materialized_realization_id"]
            )
            reasons = candidate_parameter_reasons(
                route,
                branch["request"],
                option,
                branch["parameter_constraints"],
                branch["parameter_stage"],
            )
            if reasons:
                parameter_exclusions.append(
                    {
                        "candidate_label": option["label"],
                        "reasons": reasons,
                        "scope": "this_complete_candidate_only",
                        "preparation": f"{prefix}/{option['preparation']}",
                    }
                )
                continue
        options.append(
            {
                **option,
                "label": f"branch-{ordinal + 1:04d}-{option['label']}",
                "branch_id": branch["branch_id"],
                "material_roles": preparation_materials(
                    receipt, option["materialized_realization_id"]
                ),
                "molecular_identity": molecular_identities(
                    receipt, option["materialized_realization_id"]
                ),
                "branch_label": f"branch-{ordinal + 1:04d}",
                **(
                    {"target_facts": _target_facts(root, prefix, branch, option)}
                    if "purpose" in branch
                    else {}
                ),
                "selection": {k: f"{prefix}/{v}" for k, v in option["selection"].items()},
                **{
                    key: f"{prefix}/{option[key]}"
                    for key in ("portrait", "closing_drawing", "product_stages", "preparation")
                },
            }
        )
    return {
        "label": f"branch-{ordinal + 1:04d}",
        "branch_id": branch["branch_id"],
        "changes": branch["changes"],
        "release_enzyme_id": branch["release_enzyme_id"],
        "release_method": next(
            (
                e["canonical_name"]
                for e in branch["request"]["enzyme_catalog"]["enzymes"]
                if e["enzyme_id"] == branch["release_enzyme_id"]
            ),
            None,
        ),
        "request": f"{prefix}/inputs/request.json",
        "report": f"{prefix}/report.md",
        "local_coverage": result["local_coverage"],
        "coverage": result["coverage"],
        "complete_preparations": len(options),
        "failures": failures,
        **(
            {"parameter_exclusions": parameter_exclusions}
            if branch.get("parameter_constraints")
            else {}
        ),
    }, options


def _target_facts(
    root: Path, prefix: str, branch: dict[str, Any], option: dict[str, Any]
) -> dict[str, Any]:
    portrait = json.loads(
        (root / prefix / Path(option["portrait"]).with_suffix(".json")).read_bytes()
    )
    span = portrait["loop_span"]
    additional = {}
    if any(
        c["permission"] in ("end_placements", "preparation_changes.basal_nick_enzyme_ids")
        for c in branch["changes"]
    ):
        request = branch["request"]
        if request["ends"] is not None:
            additional["end_placement"] = {
                f"{side}_bp": request["ends"][side]["payload_end_offset_bp"]
                for side in ("left", "right")
            }
        nicks = [
            e
            for r in request["basal"]["enzymes"]["role_restrictions"]
            if r["role"] == "basal_nick"
            for e in r["allowed_enzyme_ids"]
        ]
        if len(nicks) == 1:
            additional["basal_nick_enzyme_id"] = nicks[0]
    return {
        **additional,
        "loop_sequence": portrait["state"]["molecules"][0]["sequence"][
            span["start"]["offset"] : span["end"]["offset"]
        ],
        "release_enzyme_id": branch["release_enzyme_id"],
    }


def discovery_summary(
    preview: dict[str, Any],
    producer: dict[str, Any],
    branches: list[dict[str, Any]],
    options: list[dict[str, Any]],
    schedule: dict[str, Any] | None = None,
) -> dict[str, Any]:
    groups = stage_groups(options)
    return {
        "schema": "hop.scaffold-discovery-result/v1",
        "producer": producer,
        **{
            key: preview[key]
            for key in (
                "request_digest",
                "endpoint",
                "comparison_stage",
                "scaffold",
                "preparation_changes",
                "bounds",
            )
        },
        "coverage": {
            "permitted_branches": len(preview["branches"]),
            "evaluated_branches": len(branches),
            "unexamined_branches": len(preview["branches"]) - len(branches)
            if schedule is None
            else sum(t["status"] == "unexamined" for t in schedule["tasks"]),
            "evaluated_pairs": sum(b["coverage"]["evaluated_pairs"] for b in branches),
            "unexamined_pairs": sum(b["coverage"]["unexamined_pairs"] for b in branches),
            "global_route_feasibility": "not_assessed",
            **(
                {
                    "exploration_complete": not any(
                        t["status"] == "unexamined" for t in schedule["tasks"]
                    )
                    and all(b["coverage"]["unexamined_pairs"] == 0 for b in branches)
                    and all(
                        c["completion"] == "complete"
                        for b in branches
                        for c in b["local_coverage"].values()
                    )
                }
                if schedule is not None
                else {}
            ),
        },
        **({"search_schedule": schedule} if schedule is not None else {}),
        "branches": branches,
        "options": options,
        "stage_groups": groups,
        "molecules": groups[preview["comparison_stage"]],
        "selected_options": [],
    }
