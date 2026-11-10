"""Dimensioned intent schematic, never a computed or completed molecule."""

from textwrap import wrap
from typing import Any

from .control_text import PROPERTY_LABELS
from .report_primitives import page, text


def render_family_preview(summary: dict[str, Any]) -> bytes:
    intent = summary["comparison_intent"]
    members = summary["members"]
    lines = [text(25, 72, "Requested geometry · No molecular search has run", 18)]
    # This is a vocabulary diagram. No nucleotide identity or pairing is inferred.
    for y in (150, 180):
        for x1, x2, color in ((100, 190, "#177CB0"), (190, 470, "#8A949C"), (470, 550, "#36914B")):
            lines.append(f'<path d="M {x1} {y} H {x2}" stroke="{color}" stroke-width="5"/>')
    lines += [
        '<path d="M 550 150 C 620 90 620 240 550 180" fill="none" '
        'stroke="#36914B" stroke-width="5"/>',
        text(215, 143, "Supplied stem", 17),
        text(60, 225, "Open-side extent", 15),
        text(60, 246, "achieved; inspect after execution", 13),
        text(405, 110, "Loop-side extension (bp)", 16),
        text(615, 173, "Loop size (nt)", 17),
        '<path d="M 470 128 v -10 h 80 v 10" stroke="#23313B" fill="none"/>',
        text(25, 322, "Member", 17),
        text(235, 322, "Loop", 17),
        text(365, 322, "Loop-side extension", 17),
        text(600, 322, "Request intersection", 17),
    ]
    y = 353
    for member in members:
        values = member["requested_variation"]
        loop = "base domain" if values["loop_nt"] is None else f"{values['loop_nt']} nt"
        arm = (
            "base domain"
            if values["loop_side_paired_bp"] is None
            else f"{values['loop_side_paired_bp']} bp"
        )
        lines += [
            text(25, y, member["name"]),
            text(235, y, loop),
            text(365, y, arm),
            text(600, y, "Conflict: see report.md" if member["conflict"] else "Ready to search"),
        ]
        y += 29
    for heading, content in (
        (
            "Shared requirements",
            "; ".join(PROPERTY_LABELS[p] for p in summary["shared_properties"]) or "None declared",
        ),
        (
            "Material permissions",
            "; ".join(
                f"{role.replace('_', ' ')}: {policy['mode']}"
                for policies in intent["materials"].values()
                if isinstance(policies, dict)
                for role, policy in policies.items()
                if isinstance(policy, dict) and "mode" in policy
            ),
        ),
    ):
        y += 20
        lines.append(text(25, y, heading, 19))
        for line in wrap(content, 108):
            y += 23
            lines.append(text(25, y, line, 14))
    y += 36
    lines.append(
        text(
            25,
            y,
            "Exact declarations, permitted edits and finite bounds: report.md and family.json.",
            14,
        )
    )
    return page("Define your scaffold comparison", lines, height=y + 30)
