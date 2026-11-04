"""A product-first overview with scoped preparation failures at the opening level."""

from textwrap import wrap
from typing import Any

from hop_design.models.construction import ConstructionEndpoint

from ..handoff.site_conflicts import site_conflict_lines
from ..labels import endpoint_label
from .discovery_plate import discovery_plates
from .discovery_preview import dimension_requirement
from .options_report import options_report
from .report_pdf import render_report_pdf
from .report_primitives import page, text
from .terminal_plate import terminal_plates


def failure_lines(branch: dict[str, Any]) -> list[str]:
    lines = []
    if branch["release_method"]:
        lines.append(f"Release method: {branch['release_method']}.")
    explanations = {
        "hairpin-scaffold-outside-request": "The achieved hairpin misses a required dimension.",
        "clone-end-generation-incompatible": (
            "Release continuation did not produce the required insert interfaces."
        ),
        "global-actionable-site-conflict": (
            "An unintended actionable site was detected in the complete route."
        ),
    }
    for failure in branch["failures"]:
        for reason in failure["rejection_reasons"]:
            lines.append(explanations.get(reason, "Recorded rejection: " + reason))
            lines.append("Diagnostic: " + reason)
        sites = failure.get("actionable_site_conflicts", [])
        lines.extend(site_conflict_lines(sites))
        if "global-actionable-site-conflict" in failure["rejection_reasons"] and not sites:
            lines.append(
                "This disposition does not localize the responsible site; "
                "do not infer a unique sequence edit."
            )
        for mismatch in failure["scaffold_mismatches"]:
            required = mismatch["required"]
            lines.append(
                dimension_requirement(mismatch["dimension"], required).replace(": ", ": requested ")
                + f"; observed {mismatch['observed']}."
            )
        for constraint in failure["preparation_constraints"]:
            lines.append(
                f"{constraint['stage']}: {constraint['message']} "
                f"Requested {constraint['requested']}; available {constraint['available']}."
            )
    for family, coverage in branch["local_coverage"].items():
        if coverage.get("rejection_counts"):
            lines.append(f"{family} local exclusions: {coverage['rejection_counts']}.")
    lines.append(
        f"Continuation coverage: {branch['coverage']['evaluated_pairs']} examined; "
        f"{branch['coverage']['unexamined_pairs']} recorded pairs unexamined."
    )
    return list(dict.fromkeys(lines))


def discovery_report(
    summary: dict[str, Any], files: dict[str, bytes]
) -> tuple[dict[str, bytes], str]:
    coverage = summary["coverage"]
    lines = [
        "# Discover scaffolds and their preparations",
        "",
        "Requested product: " + endpoint_label(ConstructionEndpoint(summary["endpoint"])) + ".",
        f"Comparison stage: {summary['comparison_stage']}.",
        f"Requested hairpin dimensions: {summary['scaffold']}.",
        "",
        f"{len(summary['options'])} complete preparations; no selection made.",
        f"{len(summary['molecules'])} distinct molecules at the {summary['comparison_stage']} "
        "comparison stage. Identical geometry alone does not establish molecular equality.",
        f"Examined {coverage['evaluated_branches']} of {coverage['permitted_branches']} "
        f"permitted branches; {coverage['unexamined_branches']} remain unexamined.",
        "Local and continuation bounds apply separately; no global impossibility is established.",
        "",
        "[Molecular comparison and preparation boundaries](report.pdf).",
        "",
    ]
    for option in summary["options"]:
        g = option["geometry"]
        lines.append(
            f"- **{option['label']}**: loop {g['loop_nt']} nt; open side "
            f"{g['open_side_paired_positions']} paired positions; "
            f"[exact preparation]({option['preparation']})."
        )
    boundary_pages = []
    for branch in summary["branches"]:
        facts = failure_lines(branch)
        lines.extend(["", f"## {branch['label']}", ""])
        lines.extend(facts)
        lines.append(f"[Branch coverage and outcomes]({branch['report']}).")
        if not branch["failures"] and branch["complete_preparations"]:
            continue
        alternatives = [b["label"] for b in summary["branches"] if b["complete_preparations"]]
        if alternatives:
            facts.append("Complete alternatives in this packet: " + ", ".join(alternatives) + ".")
            facts.append(
                "Their explicit preparation edits are in intent/report.md; "
                "none is established as necessary or minimal."
            )
        readable = [line for fact in facts for line in wrap(fact, width=95)]
        for start in range(0, len(readable), 20):
            chunk = readable[start : start + 20]
            rows = [text(25, 70, branch["label"] + " · examined preparation boundary", 18)]
            rows.extend(text(25, 110 + i * 24, line, 15) for i, line in enumerate(chunk))
            y = 145 + len(chunk) * 24
            rows.extend(
                [
                    text(
                        25,
                        y,
                        "This outcome concerns the recorded preparation and declared bounds.",
                        15,
                    ),
                    text(
                        25,
                        y + 25,
                        "It does not establish global impossibility or a necessary repair.",
                        14,
                    ),
                ]
            )
            boundary_pages.append(
                page("Why this preparation was not obtained", rows, height=y + 60)
            )
    draw = (
        terminal_plates
        if (
            summary["endpoint"] == "adapter_ligated_hairpin"
            and any(
                d in summary["scaffold"]
                for d in ("five_prime_unpaired_nt", "three_prime_unpaired_nt")
            )
        )
        else discovery_plates
    )
    molecule_pages = (
        draw(summary, files)
        if summary["options"]
        else [v for k, v in options_report(summary, files).items() if k.endswith(".svg")]
    )
    pages = (
        molecule_pages + boundary_pages if summary["options"] else boundary_pages + molecule_pages
    )
    return {
        **{f"pages/discovery-{i + 1}.svg": p for i, p in enumerate(pages)},
        "report.pdf": render_report_pdf(tuple(pages)),
    }, "\n".join(lines) + "\n"
