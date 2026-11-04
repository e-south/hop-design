"""Whole hairpins and countable terminal tracts from verified portrait facts."""

from html import escape
from pathlib import PurePosixPath
from textwrap import wrap
from typing import Any

from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..labels import material_role_label
from .discovery_plate import comparison_frame, whole_hairpin_fragment
from .discovery_preview import dimension_requirement
from .report_primitives import page, text

TERMINAL = "#8B4A89"


def terminal_fragment(
    p: HairpinPortraitProjection, *, x: float, y: float, terminal_window_nt: int = 0
) -> str:
    """Align the outermost recorded pair; show at most 32 terminal bases per arm."""
    five, three = p.five_prime_unpaired_nt, p.three_prime_unpaired_nt
    strand = p.state.molecules[0]
    outer = p.paired_return_span.end.offset - 1
    shown_five, shown_three = min(five, 32), min(three, 32)
    anchor = x + 22 + max(shown_five, shown_three, terminal_window_nt) * 10
    rows = [f'<g data-terminal-state="{escape(p.state.state_id)}">']
    for indexes, row_y, polarity in (
        (range(five - shown_five, five + 2), y, "5\u2032"),
        (range(outer + shown_three, outer - 2, -1), y + 36, "3\u2032"),
    ):
        for index in indexes:
            relative = index - five if polarity == "5\u2032" else outer - index
            px = anchor + relative * 10
            is_terminal = index < five if polarity == "5\u2032" else index > outer
            attr = f' data-terminal-index="{index}"' if is_terminal else ""
            color = TERMINAL if is_terminal else "#176B9A"
            rows.append(
                f'<text x="{px}" y="{row_y}" text-anchor="middle" font-size="14" '
                f'fill="{color}"{attr}>{strand.sequence[index]}</text>'
            )
        first = next(iter(indexes))
        relative = first - five if polarity == "5\u2032" else outer - first
        rows.append(text(anchor + relative * 10 - 24, row_y, polarity, 13))
    for pair in p.state.pairings:
        if pair.left_index not in (five, five + 1):
            continue
        px = anchor + (pair.left_index - five) * 10
        dash = "" if pair.kind.value == "watson_crick" else ' stroke-dasharray="2 2"'
        rows.append(f'<path d="M{px},{y + 6} V{y + 21}" stroke="#176B9A"{dash}/>')
    if max(five, three) > 32:
        rows.append(text(x, y + 59, "Crop: 32 terminal bases nearest the outermost pair.", 12))
    return "\n".join([*rows, "</g>"])


def terminal_plates(summary: dict[str, Any], files: dict[str, bytes]) -> list[bytes]:
    options = summary["options"]
    portraits = [
        HairpinPortraitProjection.model_validate_json(
            files[str(PurePosixPath(option["portrait"]).with_suffix(".json"))]
        )
        for option in options
    ]
    if not portraits:
        return []
    reference = next((o for o in options if o["label"] == summary.get("baseline")), options[0])
    scale, anchor = comparison_frame(portraits)
    terminal_window = min(
        32, max(max(p.five_prime_unpaired_nt, p.three_prime_unpaired_nt) for p in portraits)
    )
    desired = "; ".join(dimension_requirement(k, v) for k, v in summary.get("scaffold", {}).items())
    pages = []
    for start in range(0, len(options), 4):
        group = list(zip(options[start : start + 4], portraits[start : start + 4], strict=True))
        rows = [text(25, 68, "Complete adapter-ligated hairpins · requested endpoint", 18)]
        for n, line in enumerate(
            wrap(desired or "Explicitly selected terminal comparison", width=104)
        ):
            rows.append(text(25, 93 + n * 19, line, 13))
        rows.extend(
            [
                text(25, 140, "Whole molecule", 18),
                text(505, 140, "Unpaired termini · exact bases", 18),
            ]
        )
        for slot, (option, portrait) in enumerate(group):
            y = 175 + slot * 135
            rows.extend(
                [
                    text(25, y, option["label"], 15),
                    whole_hairpin_fragment(
                        files[option["portrait"]], portrait, y + 5, scale=scale, anchor=anchor
                    ),
                    text(
                        505,
                        y,
                        f"5\u2032 {portrait.five_prime_unpaired_nt} nt · "
                        f"3\u2032 {portrait.three_prime_unpaired_nt} nt",
                        16,
                    ),
                    terminal_fragment(
                        portrait, x=510, y=y + 29, terminal_window_nt=terminal_window
                    ),
                    text(
                        25,
                        y + 89,
                        f"{portrait.open_side_paired_positions} open-side paired positions · "
                        f"{portrait.loop_nt}-nt loop",
                        14,
                    ),
                ]
            )
            changed = [
                material_role_label(MaterialUseRole(role)).capitalize()
                for role, value in option["material_roles"].items()
                if reference["material_roles"].get(role) != value
            ]
            rows.append(
                text(
                    25,
                    y + 109,
                    "Materials versus "
                    + reference["label"]
                    + ": "
                    + (", ".join(changed) or "same specifications"),
                    12,
                )
            )
        y = 190 + len(group) * 135
        rows.extend(
            [
                text(
                    25,
                    y,
                    "Purple: unpaired terminal bases. Pairing schematic; aligned stem; "
                    "separate enlargement scale.",
                    13,
                ),
                text(
                    25,
                    y + 23,
                    "Exact preparations: report.md and selection records. "
                    "No assembly compatibility is established.",
                    13,
                ),
            ]
        )
        pages.append(page("Specify the terminal form of your hairpin", rows, height=y + 45))
    return pages
