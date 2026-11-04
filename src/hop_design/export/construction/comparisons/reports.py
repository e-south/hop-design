"""Readable comparison intentions and bounded assessment outcomes."""

from typing import Any

from ..handoff.site_conflicts import site_conflict_lines
from .controls import prior_material_lines, schedule_lines, stage_control_lines


def preview_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Molecular comparison brief",
        "",
        f"Purpose: {summary['purpose']}; comparison stage: {summary['comparison_stage']}.",
        f"Requested endpoint: {summary['endpoint']}.",
        f"Required members: {len(summary['required_members'])}.",
        "An allowed interval does not require every value to appear in the set.",
        "",
    ]
    for name, domain in summary["dimensions"].items():
        lines.append(
            f"{name}: permitted {domain['effective_values']}; declared by {domain['declaration']}."
        )
        excluded = domain.get("excluded_intervals", [])
        if excluded:
            words = [
                str(v["minimum"])
                if v["minimum"] == v["maximum"]
                else f"{v['minimum']}-{v['maximum']}"
                for v in excluded
            ]
            lines.append(f"Excluded from the requested interval: {', '.join(words)}.")
        if domain.get("fixed_arms"):
            lines.append(f"Fixed direct-hairpin arms: {domain['fixed_arms']}.")
    lines.extend(
        [
            "",
            f"Shared hairpin properties: {summary['shared_properties']}.",
            f"Preserved material roles across members: {summary['preserve_material_roles']}.",
        ]
    )
    for member in summary["required_members"]:
        lines.append(
            f"Required {member['name']}: {member['dimensions']}; "
            f"method {member['release_enzyme_id']}."
        )
        if member.get("loop_sequence") is not None:
            lines.append(
                f"Resulting loop (hairpin strand, 5-prime to 3-prime): {member['loop_sequence']}."
            )
    lines.extend(stage_control_lines(summary))
    lines.extend(prior_material_lines(summary))
    for group in summary.get("groups", []):
        lines.append(
            f"Group {group['name']}: same {summary['comparison_stage']} product across "
            f"{', '.join(group['members'])}; distinct from the other groups."
        )
        if group.get("product_reference"):
            lines.append("This group's exact product is bound to a verified selected reference.")
    for conflict in summary["conflicts"]:
        lines.extend(
            [
                "",
                f"Conflict: {conflict['requested_field']} and {conflict['inherited_field']}.",
                conflict["explicit_edit"],
            ]
        )
    lines.extend(
        [
            "",
            "No molecular feasibility has been established. Full preparation permissions "
            "and branch limits: discovery/report.md.",
            "",
        ]
    )
    return "\n".join(lines)


def assessment_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Molecular comparison",
        "",
        f"Outcome: {summary['status']}.",
        f"Purpose: {summary['purpose']}; stage: {summary['comparison_stage']}.",
        f"{summary['distinct_molecules']['hairpin']} distinct hairpins; "
        f"{summary['distinct_molecules']['endpoint']} distinct endpoint products.",
        f"{len(summary['sets'])} compatible sets. No membership has been selected.",
        "",
    ]
    for member in summary["members"]:
        lines.append(
            f"Required {member['name']}: {member['status']} "
            f"({len(member['option_labels'])} complete options)."
        )
    lines.extend(stage_control_lines(summary))
    lines.extend(prior_material_lines(summary))
    lines.extend(schedule_lines(summary))
    for group in summary.get("groups", []):
        lines.append(
            f"Group {group['name']}: identical {summary['comparison_stage']} products "
            f"required within {', '.join(group['members'])}; different between groups."
        )
        if group.get("product_reference"):
            lines.append(f"Preserved product authority: references/{group['name']}/selection.json.")
    for item in summary["sets"]:
        lines.append(f"{item['label']}: {item['members']}")
        options = {o["label"]: o for o in summary["options"]}
        lines.append("")
        for name, label in item["members"].items():
            lines.append(
                f"- {name}: [exact preparation](discovery/{options[label]['preparation']})"
            )
            if changes := options[label].get("prior_material_changes"):
                lines.append(
                    "  Compared with the prior preparation: "
                    f"changed roles {changes['changed_roles']}; "
                    f"unchanged specifications {changes['reused_roles']}."
                )
        lines.append("")
    if summary["sets"]:
        lines.extend(
            [
                "Retrieve an explicitly chosen set with `hop-design construction select-comparison "
                "RESULT --set SET_LABEL --baseline MEMBER --out NEW_DIR`. "
                "The baseline controls presentation; it does not select a winner.",
                "",
            ]
        )
    else:
        lines.append(
            "No set is available for retrieval. Inspect missing members, rejected assignments "
            "and unexamined coverage before explicitly revising the request."
        )
    lines.extend(
        [
            "",
            f"Group coverage: {summary['group_coverage']}.",
            f"Molecular search coverage: {summary['coverage']}.",
            f"{len(summary['examined_failures'])} failed examined preparations retained.",
            "Missing options or rejected assignments are not a proof of global impossibility.",
            "Shared properties are assessed on the hairpin; exact product identity is assessed "
            "at the declared comparison stage. Local coverage remains in summary.json.",
            "",
        ]
    )
    for failure in summary["examined_failures"]:
        lines.append(
            f"{failure['branch']}: {failure['rejection_reasons']}; scope: {failure['scope']}."
        )
        lines.extend(site_conflict_lines(failure.get("actionable_site_conflicts", [])))
    for conflict in summary["conflicts"]:
        lines.append(f"Conflict: {conflict['requested_field']}; {conflict['explicit_edit']}")
    return "\n".join(lines) + "\n"
