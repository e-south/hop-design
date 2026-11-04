"""Show whole hairpins in relation to the actual product being compared."""

from copy import deepcopy
from pathlib import PurePosixPath
from textwrap import wrap
from typing import Any
from xml.etree import ElementTree as ET

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..labels import endpoint_label, material_role_label
from .hairpin_layout import HairpinLayout
from .open_region_svg import open_region_fragment
from .report_primitives import drawing_fragment, embed, page, text


def _portrait(option: dict[str, Any], files: dict[str, bytes]) -> HairpinPortraitProjection:
    path = str(PurePosixPath(option["portrait"]).with_suffix(".json"))
    return HairpinPortraitProjection.model_validate_json(files[path])


def comparison_frame(portraits: list[HairpinPortraitProjection]) -> tuple[float, float]:
    """Fit shared nucleotide spacing and stem alignment, including terminal handles."""
    left: list[float] = []
    right: list[float] = []
    for portrait in portraits:
        layout = HairpinLayout(portrait)
        ends = (0, len(portrait.state.molecules[0].sequence) - 1)
        left.extend(layout.point(i)[0] - layout.anchor - 40 for i in ends)
        right.append(layout.loop_x + layout.radius - layout.anchor + 5)
    low, high = min(left), max(right)
    scale = min(0.8, 430 / (high - low))
    return scale, 25 - low * scale


def whole_hairpin_fragment(
    content: bytes, portrait: HairpinPortraitProjection, y: int, *, scale: float, anchor: float
) -> str:
    root = ET.fromstring(drawing_fragment(content, hairpin=True))
    shape = next(e for e in root.iter() if e.get("id") == "hairpin-shape")
    offset = anchor - HairpinLayout(portrait).anchor * scale
    return (
        f'<g transform="translate({offset},{y + 28 - 111 * scale}) scale({scale})">'
        + ET.tostring(shape, encoding="unicode")
        + "</g>"
    )


def endpoint_fragment(content: bytes, y: int) -> str:
    root = ET.fromstring(content)
    shape = next((e for e in root.iter() if e.get("id") == "endpoint-shape"), None)
    if shape is None:
        return embed(content, 0, y, 860)
    group = ET.Element(
        "g", {"data-molecule-stage": "endpoint", "transform": f"translate(-270,{y - 75})"}
    )
    group.append(deepcopy(shape))
    for item in root.iter():
        if (
            item.tag.endswith("}text")
            and float(item.get("x", "0")) >= 450
            and float(item.get("y", "0")) >= 90
        ):
            group.append(deepcopy(item))
    return ET.tostring(group, encoding="unicode")


def _material_changes(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    before, after = left["material_roles"], right["material_roles"]
    lines = []
    for role in dict.fromkeys([*before, *after]):
        a, b = before.get(role), after.get(role)
        if a == b:
            continue
        label = material_role_label(MaterialUseRole(role)).capitalize()
        if a is not None and b is not None:
            lines.append(
                f"{label}: {a['length_nt']} → {b['length_nt']} nt; molecular specification changes."
            )
        else:
            lines.append(f"{label}: {'added' if a is None else 'no longer required'}.")
    return lines or [
        "Oligo specifications unchanged; inspect the permitted method and reaction prerequisites."
    ]


def discovery_plates(summary: dict[str, Any], files: dict[str, bytes]) -> list[bytes]:
    options = {o["label"]: o for o in summary["options"]}
    pages = []
    selected = bool(summary["selected_options"])
    endpoint = endpoint_label(ConstructionEndpoint(summary["endpoint"]))
    for group_number, group in enumerate(summary["stage_groups"]["endpoint"], start=1):
        candidates = [options[label] for label in group["option_labels"]]
        # Display extremes by achieved dimensions. This selects illustrations,
        # never membership, a winner or the retrieval baseline.
        candidates.sort(key=lambda o: (o["geometry"]["open_side_paired_positions"], o["label"]))
        shown = [candidates[0]] if len(candidates) == 1 else [candidates[0], candidates[-1]]
        portraits = [_portrait(option, files) for option in shown]
        scale, anchor = comparison_frame(portraits)
        window = min(26, max(p.open_side_paired_positions for p in portraits))
        geometry = shown[0]["geometry"]
        rows = [
            text(25, 69, f"Compare at: {summary['comparison_stage']} · obtain: {endpoint}", 17),
            text(
                25,
                96,
                f"Product group {group_number}: {len(candidates)} complete preparation(s); "
                + ("explicitly selected." if selected else "none selected."),
                15,
            ),
            text(25, 131, "Whole hairpins", 20),
            text(495, 131, "Open-side pairing", 20),
        ]
        for index, (option, portrait) in enumerate(zip(shown, portraits, strict=True)):
            y = 172 + index * 143
            rows.extend(
                [
                    text(
                        25,
                        y,
                        (option["label"] if selected else f"Preparation {index + 1}")
                        + f" · {portrait.open_side_paired_positions} open-side positions",
                        17,
                    ),
                    whole_hairpin_fragment(
                        files[option["portrait"]], portrait, y, scale=scale, anchor=anchor
                    ),
                    open_region_fragment(
                        portrait, portraits[0], x=500, y=y + 31, paired_window=window
                    ),
                    text(25, y + 108, option["label"], 12),
                ]
            )
        y = 190 + len(shown) * 143
        rows.extend(
            [
                text(
                    25,
                    y,
                    f"{geometry['loop_nt']}-nt loop; "
                    f"{geometry['loop_side_paired_bp']}-bp closing extension.",
                    15,
                ),
                text(
                    25,
                    y + 24,
                    "Orange: additional positions; purple: substitutions versus the first view.",
                    13,
                ),
                text(
                    25,
                    y + 45,
                    f"Crop: {window} positions nearest the stem; dashed line marks its boundary.",
                    13,
                ),
                text(
                    25,
                    y + 80,
                    "Same " + endpoint if len(shown) > 1 else "Requested " + endpoint,
                    21,
                ),
            ]
        )
        rows.append(endpoint_fragment(files[shown[0]["product_stages"]], y + 115))
        y += 255
        rows.append(text(25, y, "What changes in making it", 19))
        changes = (
            _material_changes(shown[0], shown[-1])
            if len(shown) > 1
            else ["Exact materials and unresolved reaction conditions accompany this preparation."]
        )
        for line in [part for value in changes for part in wrap(value, width=96)]:
            y += 24
            rows.append(text(25, y, line, 14))
        rows.extend(
            [
                text(
                    25,
                    y + 35,
                    (
                        "Explicit membership and exact preparations: set.json and members/."
                        if selected
                        else "Choose explicit members from report.md to retrieve preparations."
                    ),
                    13,
                ),
                text(
                    25,
                    y + 56,
                    "Pairing schematic; separate scales. Circles mark covalent joins.",
                    12,
                ),
            ]
        )
        pages.append(page("Which scaffold changes reach your product?", rows, height=y + 80))
    return pages
