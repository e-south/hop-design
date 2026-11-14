"""Dock chemistry labels to literal strand ends, without free label displacement."""

import json
from html import escape
from math import hypot

from ..label_layout import LabelPlacer
from .style import INK, LABEL_CLEARANCE, TERMINAL_SIZE
from .typography import text_width

Point = tuple[float, float]


def terminal_label_glyph(
    labels: LabelPlacer,
    point: Point,
    neighbor: Point,
    label: str,
    *,
    chemistry: str,
    kind: str = "terminus",
    attributes: dict[str, str] | None = None,
) -> str:
    x, y = point
    length = max(hypot(x - neighbor[0], y - neighbor[1]), 1e-9)
    ux, uy = (x - neighbor[0]) / length, (y - neighbor[1]) / length
    width, height = text_width(label, TERMINAL_SIZE) + 4, TERMINAL_SIZE + 5
    # Fixed terminal-relative candidates. Neither side switching nor an arbitrary
    # scene-wide collision search may detach an end label from its own nucleotide.
    candidates = []
    for extra in (0, 4, 8):
        if abs(ux) >= abs(uy):
            a = x + 14 + extra if ux >= 0 else x - 14 - extra - width
            baseline = y + TERMINAL_SIZE * 0.359
        else:
            a = x - width / 2
            baseline = y + (14 + extra + TERMINAL_SIZE if uy > 0 else -14 - extra)
        candidates.append((a, baseline - TERMINAL_SIZE, width, height, "end"))
    candidates.extend(
        (
            (x - width / 2, y - 18 - height, width, height, "above"),
            (x - width / 2, y + 18, width, height, "below"),
        )
    )
    attrs = {
        "data-terminal-chemistry": chemistry,
        "data-terminal-point": f"{x} {y}",
        **(attributes or {}),
    }

    def serial(values: dict[str, str]) -> str:
        return " ".join(f'{key}="{escape(value, quote=True)}"' for key, value in values.items())

    box = next(
        (
            b
            for b in candidates
            if all(
                b[0] + b[2] + LABEL_CLEARANCE <= a
                or a + w + LABEL_CLEARANCE <= b[0]
                or b[1] + b[3] + LABEL_CLEARANCE <= c
                or c + h + LABEL_CLEARANCE <= b[1]
                for a, c, w, h in labels.occupied
            )
        ),
        None,
    )
    if box is None:
        return (
            f'<g {serial(attrs)} data-terminal-display="metadata" '
            f'data-terminal-display-reason="local-collision"><title>{escape(chemistry)}</title></g>'
        )
    a, b, w, h, dock = box
    labels.occupied.append((a, b, w, h))
    attrs.update(
        {
            "data-label-kind": kind,
            "data-label-box": json.dumps([a, b, w, h]),
            "data-terminal-dock": dock,
        }
    )
    leader = ""
    if dock != "end":
        target = (min(max(x, a), a + w), b + h if dock == "above" else b)
        leader = (
            f'<path d="M{x + ux * 6},{y + uy * 6} L{target[0]},{target[1]}" '
            f'fill="none" stroke="{INK}" stroke-opacity=".5" stroke-width="1.5"/>'
        )
    return (
        leader + f'<text {serial(attrs)} x="{a}" y="{b + TERMINAL_SIZE}" '
        f'font-size="{TERMINAL_SIZE}" fill="{INK}">{escape(label)}'
        f"<title>{escape(chemistry)}</title></text>"
    )
