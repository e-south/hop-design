"""Static molecular repertoire and deliberate comparison; details stay beneath the plate."""

import json
from textwrap import wrap
from typing import Any

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.complete.material import MaterialUseRole

from ..labels import endpoint_label, material_role_label
from .report_pdf import render_report_pdf
from .report_primitives import drawing_fragment, embed, page, text


def options_report(summary: dict[str, Any], files: dict[str, bytes]) -> dict[str, bytes]:
    options = summary["options"]
    pages = []
    for start in range(0, max(1, len(options)), 4):
        group = options[start : start + 4]
        lines = [
            text(25, 68, "Choose a scaffold before choosing how to make it", 18),
            text(
                25,
                94,
                "Product requested: " + endpoint_label(ConstructionEndpoint(summary["endpoint"])),
                16,
            ),
            text(
                25,
                119,
                "No default selection · exact preparations linked in report.md",
                14,
            ),
        ]
        for slot, option in enumerate(group):
            y = 153 + slot * 149
            g = option["geometry"]
            label = (
                f"{option['label']} · {g['loop_nt']}-nt loop · "
                f"{g['loop_side_paired_bp']}-bp loop-side extension"
            )
            lines += [
                text(25, y, label, 17),
                embed(
                    drawing_fragment(files[option["portrait"]], hairpin=True),
                    0,
                    y - 28,
                    560,
                    shape_only=True,
                ),
                embed(drawing_fragment(files[option["closing_drawing"]]), 585, y + 12, 280),
            ]
        bottom = 172 + len(group) * 149
        c = summary["coverage"]
        lines += [
            text(
                25,
                bottom,
                f"{c['evaluated_pairs']} recorded combinations examined; "
                f"{c['unexamined_pairs']} remain unexamined. Local bounds also apply.",
                14,
            ),
            text(
                25,
                bottom + 25,
                "Drawings specify pairing architecture; loop shape does not predict conformation.",
                14,
            ),
        ]
        if not group:
            lines.append(
                text(
                    25,
                    bottom + 57,
                    "No complete option obtained. Inspect coverage before changing requirements.",
                    15,
                )
            )
        pages.append(page("Obtainable scaffold repertoire", lines, height=bottom + 88))
    return {
        **{f"pages/options-{i + 1}.svg": p for i, p in enumerate(pages)},
        "report.pdf": render_report_pdf(tuple(pages)),
    }


def selected_plate(
    summary: dict[str, Any], files: dict[str, bytes], *, context: dict[str, Any]
) -> dict[str, bytes]:
    members = summary["members"]
    pages = []
    for start in range(0, len(members), 4):
        group = members[start : start + 4]
        geometry = context["foldback"]["geometry"]
        lines = [
            text(
                25,
                65,
                "Permitted: loops " + _domain(geometry.get("loop_lengths_nt", []), "nt") + "; "
                "closing extensions " + _domain(geometry.get("annealing_arm_lengths_bp", []), "bp"),
                15,
            ),
            text(25, 91, "Explicitly selected molecules and their local differences", 18),
        ]
        dimensions = [
            json.loads(files[f"members/{m['name']}/portrait/dimensions.json"]) for m in members
        ]
        common = []
        for key, label in (
            ("loop_side_paired_bp", "bp loop-side extension"),
            ("open_side_paired_positions", "open-side paired positions"),
        ):
            values = {g[key] for g in dimensions}
            if len(values) == 1:
                common.append(f"{next(iter(values))} {label}")
        lines.append(
            text(
                25,
                117,
                "Shared in selected set: " + "; ".join(common)
                if common
                else "Exact selected architecture shown below.",
                14,
            )
        )
        for slot, member in enumerate(group):
            prefix = f"members/{member['name']}/portrait"
            g = json.loads(files[f"{prefix}/dimensions.json"])
            y = 148 + slot * 145
            lines += [
                text(
                    25,
                    y,
                    f"{member['name']} · {g['loop_nt']}-nt loop · "
                    f"{g['loop_side_paired_bp']}-bp extension",
                    17,
                ),
                embed(
                    drawing_fragment(files[f"{prefix}/projection.svg"], hairpin=True),
                    0,
                    y - 28,
                    555,
                    shape_only=True,
                ),
                embed(drawing_fragment(files[f"{prefix}/closing.svg"]), 550, y + 8, 345),
            ]
        y = 163 + len(group) * 145
        lines.append(text(25, y, _control_summary(summary), 14))
        material_lines = wrap(
            "Manufacturing changes: " + _material_summary(summary, files), width=90
        )
        for index, line in enumerate(material_lines, start=1):
            lines.append(text(25, y + 24 * index, line, 14))
        y += 24 * max(0, len(material_lines) - 1)
        if start == 0:
            stages = files[f"members/{group[0]['name']}/portrait/stages.svg"]
            lines.append(embed(stages, 0, y + 40, 900))
            y += 310
        lines.append(
            text(
                25, y + 24, "Specified pairing architecture; experimental performance untested.", 13
            )
        )
        pages.append(page("A deliberate scaffold comparison", lines, height=y + 55))
    return {
        **{f"pages/comparison-{i + 1}.svg": p for i, p in enumerate(pages)},
        "report.pdf": render_report_pdf(tuple(pages)),
    }


def _domain(values: list[int], unit: str) -> str:
    if not values:
        return "within search bounds"
    return (
        "/".join(map(str, values)) + " " + unit
        if len(values) <= 6
        else f"{len(values)} permitted values ({unit})"
    )


def _control_summary(summary: dict[str, Any]) -> str:
    controls = {c["property"]: c["status"] for c in summary["comparison_controls"]}
    labels = {
        "non_loop_sequences": "non-loop sequence",
        "regional_contacts": "contacts",
        "regional_joins": "joins",
        "terminal_chemistry": "terminal chemistry",
    }
    conserved = [
        label
        for key, label in labels.items()
        if controls.get(key) in {"required_and_verified", "observed_agreement"}
    ]
    return (
        "Verified shared: " + ", ".join(conserved)
        if conserved
        else "Inspect declared controls in report.md."
    )


def _material_summary(summary: dict[str, Any], files: dict[str, bytes]) -> str:
    roles = set()
    for member in summary["members"]:
        path = f"comparisons/{member['name']}.json"
        if path in files:
            roles.update(json.loads(files[path])["changed_material_roles"])
    return (
        ", ".join(material_role_label(MaterialUseRole(r)) for r in sorted(roles)) or "none compared"
    )
