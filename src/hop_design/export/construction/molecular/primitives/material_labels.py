"""Primer labels remain centered on their own silhouette and its outward side."""

import json
from html import escape

from hop_design.models.construction.projections.atlas import AtlasMaterialInput

from ...labels import drawing_material_label, terminal_label
from ..label_layout import LabelPlacer
from .style import ANNOTATION_SIZE, INK, LABEL_CLEARANCE
from .typography import text_width


def material_label(
    item: AtlasMaterialInput,
    box: tuple[float, float, float, float],
    labels: LabelPlacer,
    *,
    cue: str = "",
    above: bool = False,
    label_size: int = ANNOTATION_SIZE,
    positions: list[tuple[float, float]] | None = None,
) -> str:
    chemistry = [
        terminal_label("5\u2032", item.material.five_prime_end),
        terminal_label("3\u2032", item.material.three_prime_end),
    ]
    name = drawing_material_label(item.material_use.role)
    lines = [("material-name", name)]
    left, top, width, height = box
    anchor = horizontal_anchor(positions) if positions else (left + width / 2, top + height / 2)
    if positions:
        top, height = anchor[1] - 13, 26
    text_widths = [text_width(text, label_size) + 4 for _, text in lines]
    extent = max(text_widths)
    block_height = len(lines) * (label_size + 5)
    x = anchor[0] - extent / 2
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
        f'<g data-material-label-anchor="{escape(json.dumps(anchor), quote=True)}" '
        f'data-annotation-block="true" data-primer-label-side="{"above" if above else "below"}" '
        f'data-primer-chemistry="{escape(" → ".join(chemistry), quote=True)}" '
        f'data-binding-cue="{escape(cue, quote=True)}" '
        f'data-drawing-box="{x} {y} {extent} {block_height}">'
    ]
    for (kind, text), line_width in zip(lines, text_widths, strict=True):
        line_x = anchor[0] - line_width / 2
        label_box = escape(json.dumps([line_x, y, line_width, label_size + 5]), quote=True)
        rows.append(
            f'<text data-label-kind="{kind}" data-label-box="{label_box}" '
            f'x="{line_x}" y="{y + label_size}" '
            f'font-size="{label_size}" fill="{INK}">{escape(text)}</text>'
        )
        y += label_size + 5
    return "".join(rows) + "</g>"


def horizontal_anchor(positions: list[tuple[float, float]]) -> tuple[float, float]:
    """Use the left horizontal nucleotide run, excluding wedges and bends."""
    runs: list[list[tuple[float, float]]] = []
    for p in positions:
        if not runs or abs(p[1] - runs[-1][-1][1]) > 1e-6:
            runs.append([])
        runs[-1].append(p)
    candidates = [r for r in runs if len(r) > 1] or [positions]
    run = min(candidates, key=lambda r: (min(p[0] for p in r), -len(r)))
    return (
        (min(p[0] for p in run) + max(p[0] for p in run)) / 2,
        sum(p[1] for p in run) / len(run),
    )
