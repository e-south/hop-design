"""Scaffold rows and method columns from admitted comparison relationships."""

from html import escape
from pathlib import PurePosixPath
from textwrap import wrap
from typing import Any

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..labels import endpoint_label, material_role_label
from ..scaffold.closing_svg import render_closing_svg
from ..scaffold.discovery_plate import comparison_frame, endpoint_fragment, whole_hairpin_fragment
from ..scaffold.report_primitives import drawing_fragment, embed, page, text
from .controls import prior_material_lines, selected_path_prefix, stage_control_lines
from .grouped_molecules import mark_sequence_changes


def _portrait(option: dict[str, Any], files: dict[str, bytes]) -> HairpinPortraitProjection:
    return HairpinPortraitProjection.model_validate_json(
        files[str(PurePosixPath(option["portrait"]).with_suffix(".json"))]
    )


def _columns(summary: dict[str, Any]) -> tuple[list[tuple[str, int]], dict[str, tuple[str, int]]]:
    members = {m["name"]: m for m in summary["members"]}
    slots = {}
    unspecified = (
        "Any permitted method"
        if summary["endpoint"] == ConstructionEndpoint.CLONE_READY_DUPLEX.value
        else "No release method"
    )
    for group in summary["groups"]:
        counts: dict[str, int] = {}
        for name in group["members"]:
            method = members[name]["release_enzyme_id"] or unspecified
            index = counts.get(method, 0)
            counts[method] = index + 1
            slots[name] = (method, index)
    return sorted(set(slots.values())), slots


def grouped_pages(summary: dict[str, Any], files: dict[str, bytes]) -> list[bytes]:
    options = {o["label"]: o for o in summary["options"]}
    members = {m["name"]: m for m in summary["members"]}
    columns, slots = _columns(summary)
    method_names = summary["release_methods"]
    pages = []
    # A boundary sheet may show a sole verified option without asserting an admitted set.
    assignments = summary["sets"] or [
        {
            "label": "Evaluated options",
            "members": {
                name: m["option_labels"][0]
                for name, m in members.items()
                if len(m["option_labels"]) == 1
            },
        }
    ]
    for assignment in assignments:
        admitted = bool(summary["sets"])
        for row_start in range(0, len(summary["groups"]), 2):
            groups = summary["groups"][row_start : row_start + 2]
            for column_start in range(0, len(columns), 2):
                shown_columns = columns[column_start : column_start + 2]
                rows = [
                    '<g data-comparison-purpose="grouped_substrates">',
                    text(
                        25,
                        67,
                        f"{assignment['label']} · compare at {summary['comparison_stage']}",
                        16,
                    ),
                    text(
                        25,
                        93,
                        "Same product within each row; different products between rows."
                        if admitted
                        else "Requested relationships are not satisfied by an admitted set.",
                        15,
                    ),
                    text(
                        25,
                        116,
                        "Explicit membership selected"
                        if summary["selected_set"]
                        else "No membership selected",
                        13,
                    ),
                ]
                control_text = [
                    part
                    for line in (stage_control_lines(summary) + prior_material_lines(summary))[:6]
                    for part in wrap(line, 112)
                ]
                for i, line in enumerate(control_text):
                    rows.append(text(25, 140 + i * 20, line, 12))
                extra = len(control_text) * 20
                for i, (method, index) in enumerate(shown_columns):
                    rows.append(
                        text(
                            25 + i * 285,
                            151 + extra,
                            (method_names.get(method) or method)
                            + (f" · slot {index + 1}" if index else ""),
                            18,
                        )
                    )
                product_name = (
                    endpoint_label(ConstructionEndpoint(summary["endpoint"]))
                    if summary["comparison_stage"] == "endpoint"
                    else "compared hairpin"
                )
                rows.append(text(605, 151 + extra, product_name.capitalize(), 18))
                y = 180 + extra
                for group in groups:
                    rows.extend(
                        [
                            f'<g data-scaffold-group="{escape(group["name"])}">',
                            text(25, y, group["name"], 18),
                        ]
                    )
                    chosen = [
                        (name, options[assignment["members"][name]])
                        for name in group["members"]
                        if name in assignment["members"]
                    ]
                    portraits = [_portrait(o, files) for _, o in chosen]
                    if portraits:
                        scale, anchor = comparison_frame(portraits)
                        rows.append(text(25, y + 214, f"Sequence reference: {chosen[0][0]}", 12))
                    for i, column in enumerate(shown_columns):
                        names = [n for n in group["members"] if slots[n] == column]
                        x = 25 + i * 285
                        if not names:
                            rows.append(text(x, y + 55, "Not requested", 14))
                            continue
                        name = names[0]
                        rows.append(text(x, y + 25, name, 13))
                        label = assignment["members"].get(name)
                        if label is None:
                            count = len(members[name]["option_labels"])
                            rows.append(
                                text(x, y + 55, f"{count} complete options; no assignment", 12)
                            )
                            continue
                        option = options[label]
                        portrait = _portrait(option, files)
                        rows.extend(
                            [
                                f'<g transform="translate({x - 15},{y + 30}) scale(0.57)">'
                                + whole_hairpin_fragment(
                                    mark_sequence_changes(
                                        files[option["portrait"]], portrait, portraits[0]
                                    ),
                                    portrait,
                                    10,
                                    scale=scale,
                                    anchor=anchor,
                                )
                                + "</g>",
                                embed(
                                    drawing_fragment(
                                        render_closing_svg(
                                            portrait, paired_context=2, nucleotide_font_size=26
                                        ),
                                        height=170,
                                    ),
                                    x + 10,
                                    y + 86,
                                    270,
                                ),
                                text(
                                    x,
                                    y + 194,
                                    f"{portrait.loop_nt}-nt loop · {portrait.stage_role}",
                                    13,
                                ),
                            ]
                        )
                    if admitted and chosen:
                        option = chosen[0][1]
                        if summary["comparison_stage"] == "endpoint":
                            rows.append(
                                f'<g transform="translate(450,{y + 32}) scale(0.48)">'
                                + endpoint_fragment(files[option["product_stages"]], 15)
                                + "</g>"
                            )
                        else:
                            rows.append(
                                f'<g transform="translate(590,{y + 40}) scale(0.57)">'
                                + whole_hairpin_fragment(
                                    files[option["portrait"]],
                                    portraits[0],
                                    0,
                                    scale=scale,
                                    anchor=anchor,
                                )
                                + "</g>"
                            )
                        referenced = group["name"] in summary.get("product_references", {})
                        rows.append(
                            text(
                                605,
                                y + 132,
                                "Matches prior selected product"
                                if referenced
                                else "Exact identity shared",
                                13,
                            )
                        )
                        rows.append(
                            text(
                                605,
                                y + 153,
                                "at the requested stage"
                                if referenced
                                else "across this row's methods",
                                13,
                            )
                        )
                    else:
                        rows.append(text(605, y + 72, "No verified common product", 13))
                    rows.append("</g>")
                    y += 260
                rows.append(text(25, y, "What changes in making it", 18))
                y += 23
                rows.append(
                    text(25, y, "Across available preparations, including continuation pages:", 12)
                )
                for group in groups:
                    materials = [
                        options[assignment["members"][n]]
                        for n in group["members"]
                        if n in assignment["members"]
                    ]
                    if summary.get("prior_material_reference") and materials:
                        roles = sorted(
                            set().union(
                                *(o["prior_material_changes"]["changed_roles"] for o in materials)
                            )
                        )
                        labels = [material_role_label(MaterialUseRole(role)) for role in roles]
                        line = (
                            f"{group['name']}: versus prior preparation, changed "
                            + (", ".join(labels) or "no external oligo specifications")
                            + "."
                        )
                    elif len(materials) < 2:
                        line = (
                            f"{group['name']}: fewer than two assigned preparations; "
                            "differences unassessed."
                        )
                    else:
                        roles = sorted(set().union(*(o["material_roles"] for o in materials)))
                        changed = [
                            role
                            for role in roles
                            if len(
                                {
                                    o["material_roles"].get(role, {}).get("material_id")
                                    for o in materials
                                }
                            )
                            > 1
                        ]
                        labels = [material_role_label(MaterialUseRole(role)) for role in changed]
                        line = (
                            f"{group['name']}: changed "
                            + (", ".join(labels) or "no external oligo specifications")
                            + "."
                        )
                    for part in wrap(line, 112):
                        y += 22
                        rows.append(text(25, y, part, 13))
                for line in (
                    "Purple: hairpin positions differing from the named sequence reference "
                    "(equal lengths only).",
                    "Whole-molecule pairing schematics; closing-region enlargements "
                    "have a separate scale.",
                    "Loop bases are countable; drawing radius does not predict "
                    "conformation or performance.",
                    (
                        f"Exact preparations: {selected_path_prefix(summary)}report.md and "
                        f"{selected_path_prefix(summary)}members/. "
                        if summary["selected_set"]
                        else "Exact preparations: report.md and discovery/. "
                    )
                    + "Failures and unexamined requests follow.",
                ):
                    y += 23
                    rows.append(text(25, y, line, 12))
                rows.append("</g>")
                pages.append(page("Scaffolds across preparation methods", rows, height=y + 30))
    return pages
