"""A comparison-first opening for an explicitly selected insert set."""

from typing import Any

from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.variants.parameters import parameter_definition

from ..comparisons.controls import stage_control_lines
from ..labels import material_role_label


def render_insert_set_report(summary: dict[str, Any]) -> str:
    stage = "released insert" if summary["stage"] == "endpoint" else "hairpin intermediate"
    lines = [
        "# Selected molecular comparison",
        "",
        f"Compare the **{stage}**. Reference member: **{summary['baseline']}**.",
        "",
        "| Member | Hairpin loop | Substrate versus reference | Changed material roles |",
        "|---|---|---|---|",
    ]
    for name, member in summary["members"].items():
        roles = ", ".join(material_role_label(MaterialUseRole(r)) for r in member["changed_roles"])
        identity = (
            "Same modeled substrate" if member["same_substrate"] else "Different modeled substrate"
        )
        lines.append(f"| {name} | {member['loop_word']} | {identity} | {roles or 'None'} |")
    lines.extend(["", "## Intended contrast", ""])
    for name, member in summary["members"].items():
        requested = []
        for key, value in member["required_dimensions"].items():
            definition = parameter_definition(key)
            requested.append(f"{definition.label}: {value} {definition.unit}")
        if member["required_loop"]:
            requested.append(f"loop sequence: {member['required_loop']}")
        if member["required_release_method"]:
            requested.append(f"release method: {member['required_release_method']}")
        lines.append(f"- **{name}**: {', '.join(requested)}.")
    for group in summary["groups"]:
        lines.append(
            f"- **{group['name']}**: identical modeled substrate for "
            f"{', '.join(group['members'])}; distinct from the other groups."
        )
    lines.extend(["", "## Shared requirements", "", *stage_control_lines(summary)])
    for name in summary["shared_properties"]:
        lines.append(f"- Same {name.replace('_', ' ')} across the selected members.")
    for role in summary["preserve_material_roles"]:
        lines.append(
            f"- Same {material_role_label(MaterialUseRole(role))}, including terminal chemistry."
        )
    if not summary["stage_controls"] and not summary["shared_properties"]:
        lines.append("No additional shared-property controls were requested.")
    lines.extend(
        [
            "",
            "[Exact molecular differences](comparison.json) identify changes at the hairpin "
            "and released insert separately, including uncertain positional correspondence.",
            "",
            "## Oligos and preparations",
            "",
            "[Consolidated orders](oligos.csv) contain one row per exact sequence and terminal "
            "chemistry. [Member roles](oligo-uses.csv) retain every use, including shared primers.",
            "",
        ]
    )
    for name in summary["members"]:
        path = f"members/{name}"
        lines.append(
            f"- **{name}**: [measurements]({path}/views/teaching.svg), "
            f"[complete route]({path}/views/projection.svg), "
            f"[preparation and conditions]({path}/preparation/report.md)."
        )
    lines.extend(
        ["", "[Selection](design-selection.json) binds this membership and its requirements.", ""]
    )
    return "\n".join(lines)
