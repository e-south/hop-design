"""Primer labels remain centered on their own silhouette and its outward side."""

import json
from html import escape

from hop_design.models.construction.projections.atlas import AtlasMaterialInput

from ...labels import drawing_material_label, terminal_label
from ..label_layout import LabelPlacer
from .style import INK, LABEL_CLEARANCE, TERMINAL_SIZE
from .typography import text_width


def material_label(
    item: AtlasMaterialInput,
    box: tuple[float, float, float, float],
    labels: LabelPlacer,
    *,
    cue: str = "",
    above: bool = False,
) -> str:
    chemistry = [
        terminal_label("5\u2032", item.material.five_prime_end),
        terminal_label("3\u2032", item.material.three_prime_end),
    ]
    modifications = [value for value in chemistry if not value.endswith("OH")]
    name = " · ".join([drawing_material_label(item.material_use.role), *modifications])
    lines = [("material-name", name)]
    if cue:
        lines.append(("material-context", cue))
    left, top, width, height = box
    text_widths = [text_width(text, TERMINAL_SIZE) + 4 for _, text in lines]
    extent = max(text_widths)
    block_height = len(lines) * (TERMINAL_SIZE + 5)
    x = left + width / 2 - extent / 2
    y = top - block_height - 8 if above else top + height + 8
    # Preserve the horizontal anchor and outward side while resolving only nearby
    # collisions. A label must never jump toward the template or another primer.
    obstacles = [
        (b, h)
        for a, b, w, h in labels.occupied
        if x < a + w + LABEL_CLEARANCE and x + extent + LABEL_CLEARANCE > a
    ]
    for _ in range(len(obstacles) + 1):
        hit = [
            (b, h)
            for b, h in obstacles
            if y < b + h + LABEL_CLEARANCE and y + block_height + LABEL_CLEARANCE > b
        ]
        if not hit:
            break
        y = (
            min(b for b, _ in hit) - block_height - LABEL_CLEARANCE
            if above
            else max(b + h for b, h in hit) + LABEL_CLEARANCE
        )
    labels.occupied.append((x, y, extent, block_height))
    rows = [
        f'<g data-annotation-block="true" data-primer-label-side="{"above" if above else "below"}" '
        f'data-primer-chemistry="{escape(" → ".join(chemistry), quote=True)}" '
        f'data-drawing-box="{x} {y} {extent} {block_height}">'
    ]
    for (kind, text), line_width in zip(lines, text_widths, strict=True):
        line_x = left + width / 2 - line_width / 2
        label_box = escape(json.dumps([line_x, y, line_width, TERMINAL_SIZE + 5]), quote=True)
        rows.append(
            f'<text data-label-kind="{kind}" data-label-box="{label_box}" '
            f'x="{line_x}" y="{y + TERMINAL_SIZE}" '
            f'font-size="{TERMINAL_SIZE}" fill="{INK}">{escape(text)}</text>'
        )
        y += TERMINAL_SIZE + 5
    return "".join(rows) + "</g>"
