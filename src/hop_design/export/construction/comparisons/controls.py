"""Name the molecular stage and extent of each regional comparison."""

from typing import Any

from hop_design.models.construction.complete.material import MaterialUseRole

from ..labels import material_role_label

_LABELS = {
    "non_loop_sequences": "sequences outside the loop-derived region",
    "non_loop_pairing": "pairing outside the loop-derived region",
    "terminal_chemistry": "terminal chemistry",
}


def stage_control_lines(summary: dict[str, Any]) -> list[str]:
    lines = []
    for control in summary.get("stage_controls", []):
        stage = "hairpin" if control["stage"] == "hairpin" else "requested endpoint"
        scope = "whole set" if control["scope"] == "set" else f"group {control['group']}"
        lines.append(f"Required at {stage}, {scope}: same {_LABELS[control['property']]}.")
    if lines and summary.get("sets"):
        lines.append("Every available set passes these stage-specific controls.")
    elif lines and all(c.get("status") == "shared" for c in summary["stage_controls"]):
        lines.append("The selected members pass these stage-specific controls.")
    for example in summary.get("stage_control_examples", [])[:1]:
        for observation in example["controls"]:
            if observation["status"] == "shared":
                continue
            details = ", ".join(observation["different_members"])
            if observation["status"] == "unassessed":
                details = "insufficient members or missing/ambiguous region ancestry"
            lines.append(
                f"Examined assignment: {_LABELS[observation['property']]} "
                f"at {observation['stage']} {observation['status']} ({details})."
            )
    return lines


def prior_material_lines(summary: dict[str, Any]) -> list[str]:
    prior = summary.get("prior_material_reference")
    if prior is None:
        return []
    roles = ", ".join(material_role_label(MaterialUseRole(r)) for r in prior["required_roles"])
    lines = [
        f"Reuse from the verified prior preparation: {roles} (sequence and terminal chemistry).",
        "Product preservation and material agreement among new members "
        "remain separate requirements.",
    ]
    for name, changes in summary.get("prior_material_changes", {}).items():
        changed = ", ".join(
            material_role_label(MaterialUseRole(r)) for r in changes["changed_roles"]
        )
        lines.append(f"{name}: versus the prior preparation, changed {changed or 'no materials'}.")
    return lines


def selected_path_prefix(summary: dict[str, Any]) -> str:
    return "" if summary.get("report_at_root") else "../"


def schedule_lines(summary: dict[str, Any]) -> list[str]:
    schedule = summary.get("search_schedule")
    if schedule is None:
        return []
    budget = schedule["budget"]
    missing = sum(not t["option_labels"] for t in schedule["targets"])
    reused = sum(t["status"] == "reused" for t in schedule["tasks"])
    remaining = sum(t["status"] == "unexamined" for t in schedule["tasks"])
    return [
        f"Required-first search: {budget['used_tasks']} of "
        f"{budget['max_evaluated_tasks']} shared task slots used; "
        f"{reused} tasks reused complete options.",
        f"{missing} molecular targets remain missing; {remaining} tasks unexamined. "
        "Local quotas and continuation coverage remain separate from set-assignment coverage.",
    ]
