"""Describe compatible preparations without selecting or overstating coverage."""

from typing import Any

from .control_text import PROPERTY_LABELS


def render_matching_report(summary: dict[str, Any]) -> str:
    reference = summary["reference"]
    rows = [
        "# Find preparations for your comparison",
        "",
        f"Declared reference: **{reference['member']}**, complete choice {reference['choice']}.",
        "[Reference molecule](reference/projection.svg) · "
        "[Preparation](reference/preparation/report.md)",
        "",
        "Required agreement: "
        + ", ".join(PROPERTY_LABELS[p] for p in summary["shared_properties"])
        + ".",
        "",
        "Every request and requirement remains unchanged. "
        "Compatible alternatives are not selected automatically.",
        "",
        "## Examined alternatives",
        "",
        "| Member | Pair | Result | Shared requirements | Inspect |",
        "| --- | --- | --- | --- | --- |",
    ]
    for member in summary["members"]:
        for candidate in member["candidates"]:
            prefix = f"| {member['name']} | {candidate['ordinal']} | "
            if not candidate["choices"]:
                rows.append(
                    prefix + f"{candidate['status']} | Not assessed | "
                    f"[Outcome]({candidate['outcome']}) |"
                )
            for choice in candidate["choices"]:
                finding = (
                    "Compatible"
                    if choice["compatible"]
                    else "Disagrees: "
                    + ", ".join(PROPERTY_LABELS[p] for p in choice["differing_properties"])
                )
                rows.append(
                    prefix + f"Complete | {finding} | "
                    f"[Molecule]({choice['portrait']}) · "
                    f"[Preparation]({choice['preparation']}) |"
                )
    c = summary["coverage"]
    rows += [
        "",
        "## Choose explicitly and retrieve",
        "",
        "Each complete choice in `summary.json` supplies `bundle_path` and `selection_path` "
        "for a `hop.construction-set/v1` request.",
        "Name your members and baseline, retain these shared requirements, "
        "and run `construction select-set`. Paths are relative to this packet; put "
        "your selection request beside it and prefix its paths with the packet directory.",
        "A compatible outcome can also be explicitly admitted with "
        "`construction reconcile-family --outcome candidates/MEMBER/PAIR/outcome`.",
        "",
        "## Coverage",
        "",
        f"{c['evaluated_pairs']}/{c['recorded_pairs']} recorded pairs examined "
        f"under a {c['max_continuations']}-continuation bound.",
    ]
    for member in summary["members"]:
        rows.append(
            f"- {member['name']}: {member['evaluated_pairs']}/"
            f"{member['recorded_pairs']} recorded pairs examined; "
            f"{member['unexamined_pairs']} unexamined."
        )
    rows += [
        "",
        "Local search completion and quotas remain recorded per member. A missing match "
        "is not global impossibility; a local witness is not a complete preparation.",
        "Original outcomes remain under `family/`; the requirements are unchanged.",
        "",
    ]
    return "\n".join(rows)
