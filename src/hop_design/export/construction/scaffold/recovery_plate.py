"""A compact decision trace from local choices to the completed requested product."""

from hop_design.models.construction.projections.family_report import (
    ConstructionFamilyReportProjection,
)

from .report_primitives import drawing_fragment, embed, page, text


def recovery_plate(report: ConstructionFamilyReportProjection, files: dict[str, bytes]) -> bytes:
    recovery = report.recovery
    if recovery is None:
        raise ValueError("A recovery plate requires verified revision facts.")
    member = next(m for m in report.members if m.name == recovery.target_member)
    choice = member.choices[0]
    lines = [
        text(25, 72, f"{recovery.source_member}: {recovery.prior_status} → {member.status}", 19),
        text(25, 105, "Local choices", 19),
        text(25, 132, "Recorded closing-region witnesses; not complete preparations.", 15),
    ]
    for i, local in enumerate(recovery.foldback_choices[:6]):
        selected = "chosen" if local.selected else "not continued here"
        lines.append(
            text(
                25,
                163 + i * 25,
                f"{local.loop_nt}-nt loop · {local.loop_side_paired_bp}-bp extension · {selected}",
                16,
            )
        )
    y = 173 + min(6, len(recovery.foldback_choices)) * 25
    if len(recovery.foldback_choices) > 6:
        lines.append(
            text(
                25,
                y,
                "First six choices shown; every witness and selection is retained in summary.json.",
                13,
            )
        )
        y += 25
    preference = (
        f"Declared preference: {recovery.preferred_loop_nt}-nt loop"
        if recovery.preferred_loop_nt is not None
        else "Explicit local selection; no preference was recorded."
    )
    lines += [
        text(25, y + 9, preference, 19),
        text(
            25,
            y + 38,
            "Preference records intent; it does not rank alternatives or choose a witness.",
            14,
        ),
        text(25, y + 80, "Complete preparation", 20),
        embed(drawing_fragment(files[choice.stage_drawing], height=190), 0, y + 100, 900),
        text(
            25,
            y + 310,
            "Original request and local choices remain preserved; exact preparation: report.md.",
            14,
        ),
        text(
            25,
            y + 335,
            "Local coverage is bounded. Preparation performance remains unevaluated.",
            14,
        ),
    ]
    return page("Continue an explicit molecular choice", lines, height=y + 360)
