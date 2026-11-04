"""Read a discovery intention in molecular vocabulary before its preparation branches."""

from typing import Any

from hop_design.models.construction import ConstructionEndpoint

from ..labels import endpoint_label

DIMENSIONS = {
    "open_side_paired_positions": ("Open-side pairing", "positions"),
    "loop_nt": ("Loop", "nt"),
    "loop_side_paired_bp": ("Loop-side extension", "bp"),
    "five_prime_unpaired_nt": ("5\u2032 unpaired terminal tract", "nt"),
    "three_prime_unpaired_nt": ("3\u2032 unpaired terminal tract", "nt"),
}


def dimension_requirement(dimension: str, interval: dict[str, int]) -> str:
    label, unit = DIMENSIONS[dimension]
    low, high = interval["minimum"], interval["maximum"]
    return f"{label}: {low if low == high else f'{low}-{high}'} {unit}"


def preview_report(summary: dict[str, Any]) -> str:
    bounds = summary["bounds"]
    lines = [
        "# Requested scaffold and permitted preparations",
        "",
        endpoint_label(ConstructionEndpoint(summary["endpoint"])).capitalize()
        + f"; compare at: {summary['comparison_stage']}.",
        "",
        "## Effective molecular requirements",
        "",
    ]
    lines.extend(dimension_requirement(k, v) for k, v in summary["scaffold"].items())
    if not summary["scaffold"]:
        lines.append("Use the product's declared geometry domains.")
    lines.extend(["", "## Material policies", ""])
    lines.extend(
        f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in summary["material_policies"].items()
    )
    lines.extend(
        [
            "Fixed materials retain their sequence and chemistry. A derived material may change.",
            "",
            f"Adapter redesign: {summary['preparation_changes']['adapter_redesign']}.",
            f"{bounds['permitted_branches']} preparation branches; "
            f"at most {bounds['max_branches']} will be examined.",
            f"Each examined branch permits {bounds['max_continuations_per_branch']} continuations.",
            "Local search quotas remain in force within each branch.",
            "",
            "These settings are unevaluated. The achieved scaffold is checked after construction.",
            "Catalog membership describes a recorded method, not laboratory stock.",
            "",
        ]
    )
    for conflict in summary["conflicts"]:
        lines.extend(
            [
                f"Conflict: {conflict['requested_field']} = {conflict['requested_value']} and "
                f"{conflict['inherited_field']} = {conflict['inherited_value']}.",
                conflict["explicit_edit"],
                "",
            ]
        )
    for target in summary.get("search_targets", []):
        if target.get("parameter_scope") == "outside_selected_region":
            lines.append(
                f"Required target {target['target_id']} remains outside this selected "
                "evaluation region; its membership is retained, not fulfilled by this round."
            )
    for index, branch in enumerate(summary["branches"], start=1):
        lines.append(f"## Preparation branch {index}")
        lines.append(f"Release method: {branch['release_enzyme_id'] or 'not applicable'}.")
        for change in branch["changes"]:
            lines.append(f"- {change['field']}: {change['before']} → {change['after']}.")
        lines.append("")
    return "\n".join(lines) + "\n"
