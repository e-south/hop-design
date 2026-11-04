"""One deterministic task traversal shared by execution and saved-packet admission."""

from collections.abc import Callable
from typing import Any

from .targets import matching_options, task_decision

type EvaluateBranch = Callable[[dict[str, Any], int], tuple[dict[str, Any], list[dict[str, Any]]]]


def evaluate_plan(
    preview: dict[str, Any], evaluate: EvaluateBranch
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    branches: list[dict[str, Any]] = []
    options: list[dict[str, Any]] = []
    budget = preview["bounds"]["max_branches"]
    scheduled = "search_targets" in preview
    targets = preview.get("search_targets", [])
    tasks = []
    plan = preview["branches"] if scheduled else preview["branches"][:budget]
    for branch in plan:
        decision, reused = (
            task_decision(branch, targets, options, used=len(branches), budget=budget)
            if scheduled
            else ("evaluate", {})
        )
        row = {
            "branch_id": branch["branch_id"],
            "purpose": branch.get("purpose", "optional"),
            "target_ids": branch.get("target_ids", []),
            "status": decision,
            "reused_options": reused,
        }
        if decision == "evaluate":
            record, complete = evaluate(branch, len(branches))
            branches.append(record)
            options.extend(complete)
            row.update(status="evaluated", branch_label=record["label"])
        tasks.append(row)
    schedule = None
    if scheduled:
        schedule = {
            "strategy": "required_members_first/v1",
            "targets": [{**t, "option_labels": matching_options(t, options)} for t in targets],
            "tasks": tasks,
            "budget": {
                "max_evaluated_tasks": budget,
                "max_continuations_per_task": preview["bounds"]["max_continuations_per_branch"],
                "used_tasks": len(branches),
            },
            "original_domain_preserved": True,
            "scope": "bounded_targeted_and_optional_tasks",
        }
    return branches, options, schedule
