"""Molecular edit preview prose; it does not evaluate or infer construction outcomes."""

from typing import Any


def edit_preview_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Edit the retained scaffold",
        "",
        "Preview only. No complete molecule has been evaluated for this edit.",
        "Original material policies, geometry and method permissions remain active.",
        "",
    ]
    for change in summary["changes"]:
        lines.append(
            f"{change['stage']} {change['region']}: "
            f"{change['before']} → {change['after']} ({change['field']})."
        )
    lines += ["", f"Status: {summary['status']}."]
    for conflict in summary["conflicts"]:
        lines.append(f"Conflict at {conflict['inherited_field']}: {conflict['explicit_edit']}")
    lines += [
        "",
        "Evaluation uses the unchanged branch and continuation budgets. "
        "Required words are targets, not guaranteed complete preparations.",
        "",
    ]
    return "\n".join(lines)
