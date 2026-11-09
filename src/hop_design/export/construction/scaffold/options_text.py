"""Reading order for complete options; no inference of selection or feasibility."""

from typing import Any

from hop_design.models.construction import ConstructionEndpoint

from ..labels import endpoint_label


def render_options_text(summary: dict[str, Any]) -> str:
    coverage = summary["coverage"]
    lines = [
        "# Choose a complete scaffold",
        "",
        f"Requested product: {endpoint_label(ConstructionEndpoint(summary['endpoint']))}.",
        f"{len(summary['options'])} complete product options; no option selected.",
        "[Whole-molecule repertoire](report.pdf). Labels apply within this packet.",
        "",
    ]
    if coverage["unexamined_pairs"]:
        lines += [
            f"Exploration incomplete: {coverage['unexamined_pairs']} recorded pairs remain.",
            "Run the same request with an explicitly larger continuation budget to examine more.",
            "",
        ]
    lines += ["## Complete molecules", ""]
    for option in summary["options"]:
        g = option["geometry"]
        lines += [
            f"- **{option['label']}**: loop {g['loop_nt']} nt; loop-side extension "
            f"{g['loop_side_paired_bp']} bp; "
            f"open-side {g['open_side_paired_positions']} paired positions. "
            f"[Whole molecule]({option['portrait']}); [preparation]({option['preparation']}).",
        ]
    lines += ["", "## Examined preparation boundaries", ""]
    for row in summary["candidates"]:
        if row["status"] != "complete":
            lines += [f"- [Combination {row['ordinal'] + 1}: {row['status']}]({row['outcome']})."]
    lines += [
        "",
        f"Examined {coverage['evaluated_pairs']} of {coverage['recorded_pairs']} recorded pairs.",
        "Local search termination and each continuation's accounting remain in summary.json.",
        "Use a comparison request to require shared properties across selected products.",
        "",
    ]
    return "\n".join(lines)
