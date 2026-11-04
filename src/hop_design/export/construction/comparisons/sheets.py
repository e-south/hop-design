"""Compact comparison forms assembled only from replay-verified projections."""

from collections import Counter
from pathlib import PurePosixPath
from textwrap import wrap
from typing import Any

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..handoff.site_conflicts import site_conflict_lines
from ..labels import endpoint_label
from ..scaffold.closing_svg import render_closing_svg
from ..scaffold.discovery_plate import comparison_frame, endpoint_fragment, whole_hairpin_fragment
from ..scaffold.open_region_svg import open_region_fragment
from ..scaffold.report_pdf import render_report_pdf
from ..scaffold.report_primitives import drawing_fragment, embed, page, text
from .controls import (
    prior_material_lines,
    schedule_lines,
    selected_path_prefix,
    stage_control_lines,
)
from .grouped_sheets import grouped_pages
from .materials import material_rows


def _caption(rows: list[str], value: str, y: int, *, size: int = 14) -> int:
    for line in wrap(value, 104):
        y += 23
        rows.append(text(25, y, line, size))
    return y


def _set_pages(summary: dict[str, Any], files: dict[str, bytes]) -> list[bytes]:
    options = {o["label"]: o for o in summary["options"]}
    pages = []
    for group in summary["sets"]:
        members = list(group["members"].items())
        baseline_name = summary.get("presentation_baseline") or members[0][0]
        baseline_option = options[group["members"][baseline_name]]
        baseline_portrait = HairpinPortraitProjection.model_validate_json(
            files[str(PurePosixPath(baseline_option["portrait"]).with_suffix(".json"))]
        )
        for start in range(0, len(members), 4):
            shown = members[start : start + 4]
            names = [name for name, _ in shown]
            candidates = [options[label] for _, label in shown]
            portraits = [
                HairpinPortraitProjection.model_validate_json(
                    files[str(PurePosixPath(o["portrait"]).with_suffix(".json"))]
                )
                for o in candidates
            ]
            scale, anchor = comparison_frame(portraits)
            show_open = (
                len({p.open_side_paired_positions for p in [*portraits, baseline_portrait]}) > 1
            )
            alternative = summary["purpose"] == "preparation_alternatives"
            endpoint = endpoint_label(ConstructionEndpoint(summary["endpoint"]))
            rows = [
                f'<g data-comparison-purpose="{summary["purpose"]}">',
                text(
                    25,
                    68,
                    f"{group['label']} · compare at {summary['comparison_stage']} "
                    f"· obtain {endpoint}",
                    15,
                ),
                text(
                    25,
                    94,
                    "Explicitly selected set"
                    if summary["selected_set"]
                    else "No membership selected",
                    14,
                ),
            ]
            y = 120
            if alternative:
                y = _caption(
                    rows,
                    "Common product: exact sequence, contacts, topology and terminal "
                    "chemistry agree at the comparison stage.",
                    y,
                )
                if summary["comparison_stage"] == "endpoint":
                    rows.append(endpoint_fragment(files[candidates[0]["product_stages"]], y + 15))
                else:
                    rows.append(
                        whole_hairpin_fragment(
                            files[candidates[0]["portrait"]],
                            portraits[0],
                            y + 15,
                            scale=scale,
                            anchor=anchor,
                        )
                    )
                y += 150
            shared = (
                ", ".join(k.replace("_", " ") for k in summary["shared_properties"])
                or "none required"
            )
            y = _caption(rows, f"Shared hairpin properties: {shared}.", y)
            for line in (stage_control_lines(summary) + prior_material_lines(summary))[:6]:
                y = _caption(rows, line, y, size=12)
            y += 35
            rows.extend(
                [text(25, y, "Whole hairpins", 19), text(505, y, "Countable closing region", 19)]
            )
            for (name, _), option, portrait in zip(shown, candidates, portraits, strict=True):
                geometry = option["geometry"]
                method = f" ({option['release_method']})" if option["release_method"] else ""
                y = _caption(
                    rows,
                    f"{name}{method}: {geometry['loop_nt']}-nt loop · "
                    f"{geometry['loop_side_paired_bp']}-bp extension · "
                    f"{geometry['open_side_paired_positions']} open-side positions",
                    y + 7,
                )
                rows.append(
                    whole_hairpin_fragment(
                        files[option["portrait"]], portrait, y + 7, scale=scale, anchor=anchor
                    )
                )
                crop = render_closing_svg(portrait, paired_context=2, nucleotide_font_size=18)
                rows.append(embed(drawing_fragment(crop, height=170), 505, y + 10, 290))
                if show_open:
                    window = min(
                        26,
                        max(p.open_side_paired_positions for p in [*portraits, baseline_portrait]),
                    )
                    rows.append(
                        open_region_fragment(
                            portrait,
                            baseline_portrait,
                            x=70,
                            y=y + 95,
                            paired_window=window,
                        )
                    )
                    y += 50
                y += 123
                rows.append(text(25, y, f"{option['label']} · {portrait.stage_role}", 11))
            if (
                not alternative
                and summary["comparison_stage"] == "hairpin"
                and portraits[0].stage_role == "intermediate"
            ):
                y = _caption(
                    rows,
                    "Hairpins shown are intermediates. Representative supported continuation:",
                    y + 8,
                )
                rows.append(endpoint_fragment(files[candidates[0]["product_stages"]], y + 12))
                y += 147
            material_page = None
            if len(shown) > 2:
                changes, material_y = material_rows(
                    candidates,
                    names,
                    75,
                    baseline=(baseline_name, baseline_option),
                )
                material_page = page(
                    f"{group['label']}: preparation changes", changes, height=material_y + 40
                )
                # Keep the molecular sheet at print scale; detailed changes follow it.
                y = _caption(rows, "Preparation changes follow on the next page.", y + 15)
            else:
                changes, y = material_rows(
                    candidates,
                    names,
                    y + 35,
                    baseline=(baseline_name, baseline_option),
                )
                rows.extend(changes)
            if show_open:
                y = _caption(
                    rows,
                    f"Open-side crop: orange positions are added; purple bases "
                    f"differ from {baseline_name}. Stem boundary is dashed.",
                    y,
                    size=12,
                )
            y = _caption(
                rows,
                "Pairing schematics; enlargements use separate scales. Loop bases are countable; "
                "radius is not a conformation prediction. Circles mark covalent joins.",
                y + 12,
                size=12,
            )
            y = _caption(
                rows,
                (
                    f"Exact preparations: {selected_path_prefix(summary)}members/; "
                    f"consolidated oligos: {selected_path_prefix(summary)}oligos.csv. "
                    if summary["selected_set"]
                    else "Exact preparations: report.md and discovery/. "
                    "Select a named set to retrieve "
                    "consolidated oligos. "
                )
                + "Reaction performance and recovery remain unresolved.",
                y,
                size=12,
            )
            rows.append("</g>")
            pages.append(
                page(
                    "Alternative preparations of one product"
                    if alternative
                    else "Specify a molecular comparison",
                    rows,
                    height=y + 25,
                )
            )
            if material_page is not None:
                pages.append(material_page)
    return pages


def _boundary_pages(summary: dict[str, Any]) -> list[bytes]:
    available = bool(summary["sets"])
    lines = [
        "Complete requested sets are available."
        if available
        else "No complete requested set was found in the evaluated pool.",
        "A missing member or failed preparation does not establish global impossibility.",
    ]
    lines.extend(
        f"Required {m['name']}: {len(m['option_labels'])} complete options"
        + ("." if m["option_labels"] else "; missing from the evaluated pool.")
        for m in summary["members"]
    )
    lines.extend(stage_control_lines(summary))
    lines.extend(prior_material_lines(summary))
    lines.extend(schedule_lines(summary))
    failed = Counter(
        (f["branch"], tuple(f["rejection_reasons"]), f["scope"])
        for f in summary["examined_failures"]
    )
    lines.extend(
        f"{branch}: {count} examined preparation(s) rejected ({', '.join(reasons)}); "
        f"scope: {scope.replace('_', ' ')}."
        for (branch, reasons, scope), count in failed.items()
    )
    for failure in summary["examined_failures"]:
        lines.extend(site_conflict_lines(failure.get("actionable_site_conflicts", [])))
    coverage, groups = summary["coverage"], summary["group_coverage"]
    partial_local = sum(
        any(c["completion"] != "complete" for c in branch["coverage"].values())
        for branch in summary.get("local_coverage", [])
    )
    lines.extend(
        [
            f"{coverage['evaluated_pairs']} continuations examined; "
            f"{coverage['unexamined_pairs']} recorded continuations unexamined; "
            f"{coverage['unexamined_branches']} search tasks unexamined.",
            f"{partial_local} evaluated tasks retain incomplete local search. "
            "Complete requested members do not imply an exhausted permitted domain.",
            f"{groups['evaluated_assignments']} member assignments examined; "
            f"{groups['unexamined_assignments']} unexamined.",
            (
                "Detailed failures, constraints and exact preparation links: "
                + (
                    f"{selected_path_prefix(summary)}comparison-selection.json and "
                    f"{selected_path_prefix(summary)}report.md."
                    if summary["selected_set"]
                    else "report.md and summary.json."
                )
            ),
        ]
    )
    lines.extend(
        f"{count} assignment(s) rejected: {reason.replace('_', ' ')}."
        for reason, count in groups["rejections"].items()
    )
    wrapped = [part for line in lines for part in wrap(line, 96)]
    return [
        page(
            "Requested family and examined boundaries",
            [text(25, 80 + j * 24, line, 15) for j, line in enumerate(wrapped[i : i + 28])],
            height=160 + 24 * len(wrapped[i : i + 28]),
        )
        for i in range(0, len(wrapped), 28)
    ]


def comparison_files(summary: dict[str, Any], files: dict[str, bytes]) -> dict[str, bytes]:
    pages = grouped_pages(summary, files) if summary.get("groups") else _set_pages(summary, files)
    boundaries = _boundary_pages(summary)
    pages = pages + boundaries if summary["sets"] else boundaries + pages
    return {
        "report.pdf": render_report_pdf(tuple(pages)),
        **{f"pages/comparison-{i}.svg": content for i, content in enumerate(pages, start=1)},
    }
