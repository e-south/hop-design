"""Put the user's next actions ahead of the complete technical record."""

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.projections.family_report import (
    ConstructionFamilyReportProjection,
)

from ..labels import endpoint_label
from .control_text import PROPERTY_LABELS, control_label


def retrieval_text(report: ConstructionFamilyReportProjection) -> list[str]:
    md = []
    if report.compared_properties:
        md += [
            "Intended comparison: "
            + ", ".join(PROPERTY_LABELS[p] for p in report.compared_properties)
            + ". This states the requested contrast; the controls below report what was verified.",
            "",
        ]
    md += ["## Retrieve preparations", ""]
    if report.selection_set_id:
        md += [
            "[Selected set](selected/report.md) · [Order specifications](selected/oligos.csv) · "
            "[Member and material uses](selected/oligo-uses.csv) · "
            "[Portable selection](selected/set.json)",
            "",
        ]
    else:
        md += ["No set has been selected. Individual preparations below remain available.", ""]
    md += ["| Member | Obtained molecule | Membership | Preparation |", "| --- | --- | --- | --- |"]
    for member in report.members:
        if not member.choices:
            md.append(
                f"| {member.name} | No completed molecule: {member.status} | "
                "Not selected | See outcome below |"
            )
        for choice in member.choices:
            endpoint = endpoint_label(ConstructionEndpoint(choice.endpoint))
            membership = "Not selected"
            if choice.selected:
                membership = (
                    f"Selected as {choice.selection_name}"
                    if choice.selection_name != member.name
                    else "Selected"
                )
            md.append(
                f"| {member.name} | {choice.geometry['loop_nt']}-nt loop, "
                f"{choice.geometry['loop_side_paired_bp']}-bp extension; "
                f"hairpin {choice.stage_role} "
                f"→ {endpoint} | {membership} | "
                f"[Exact preparation]({choice.preparation}) · [Molecule]({choice.portrait}) |"
            )
    md += [
        "",
        "Each preparation includes its exact materials and terminal chemistry.",
        "",
    ]
    if report.recovery:
        r = report.recovery
        md += [
            "## Continue an explicit choice",
            "",
            f"{r.source_member}: {r.prior_status} → completed preparation.",
            "",
            (
                f"Declared preference: {r.preferred_loop_nt}-nt loop."
                if r.preferred_loop_nt is not None
                else "No selection preference was recorded."
            ),
            "Local witnesses are not complete preparations; exact choices and "
            "selected identity remain in summary.json.",
            "",
            "[Original request and outcomes](family/history/parent/report.md)",
            "",
        ]
    md += ["## Comparison controls", ""]
    controls = report.selected_controls or report.family_controls
    scope = "selected set" if report.selected_controls else "requested family"
    if controls:
        if len(controls[0].members) == 1:
            md += [
                "Single selected molecule; between-member agreement is not assessed."
                if report.selected_controls
                else "Single family choice; between-member agreement is not assessed.",
                "Individual achieved properties remain available in its molecular record.",
                "",
            ]
        md += [
            f"Scope: {scope}; reference: {controls[0].reference or 'none'}. "
            "Required agreement is distinct from agreement observed after construction.",
            "",
            "| Molecular property | Finding |",
            "| --- | --- |",
        ]
        for c in controls:
            label = control_label(c)
            if c.property in report.compared_properties and c.status == "different":
                label = "Intended variation; observed difference"
            md.append(f"| {PROPERTY_LABELS[c.property]} | {label} |")
    missing = sorted({m for c in report.family_controls for m in c.unassessed_members})
    if missing:
        md += [
            "",
            "Not assessed across the full requested family: "
            + ", ".join(missing)
            + ". Missing molecular evidence is not agreement or global impossibility.",
        ]
    return md
