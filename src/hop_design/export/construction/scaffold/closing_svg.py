"""Countable closing-region crop of the same recorded whole-hairpin drawing."""

from html import escape
from itertools import pairwise

from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..hairpin_svg import GREEN, INK
from .hairpin_layout import HairpinLayout


def render_closing_svg(
    p: HairpinPortraitProjection, *, paired_context: int = 8, nucleotide_font_size: int = 14
) -> bytes:
    layout = HairpinLayout(p)
    ls, le = p.loop_span.start.offset, p.loop_span.end.offset
    sequence = p.state.molecules[0].sequence
    pairs = [
        pair
        for pair in p.state.pairings
        if ls - min(paired_context, p.loop_side_paired_bp) <= pair.left_index < ls
    ]
    indices = sorted(
        {i for pair in pairs for i in (pair.left_index, pair.right_index)} | set(range(ls, le))
    )
    x0 = min(layout.point(i)[0] for i in indices)
    scale = 3.5
    width = max(400, (layout.loop_x + layout.radius - x0) * scale + 115)

    def xy(i: int) -> tuple[float, float]:
        x, y = layout.point(i)
        return 35 + (x - x0) * scale, 40 + (y - 111) * scale

    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="90mm" height="49.5mm" '
        f'viewBox="0 0 {width} 220">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<g font-family="Arial, Helvetica, sans-serif" fill="{INK}">',
        f'<text x="20" y="20" font-size="16">{p.loop_side_paired_bp}-bp extension · '
        f"{p.loop_nt}-nt loop</text>",
    ]
    for i, j in pairwise(indices):
        if j != i + 1:
            continue
        a, b = xy(i), xy(j)
        rows.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{GREEN}"/>')
    for pair in pairs:
        a, b = xy(pair.left_index), xy(pair.right_index)
        dash = "" if pair.kind.value == "watson_crick" else ' stroke-dasharray="3 3"'
        rows.append(
            f'<line x1="{a[0]}" y1="{a[1] + 10}" x2="{b[0]}" y2="{b[1] - 10}" '
            f'stroke="{GREEN}"{dash}/>'
        )
    for boundary in p.join_boundaries:
        if boundary - 1 in indices and boundary in indices:
            a, b = xy(boundary - 1), xy(boundary)
            rows.append(
                f'<circle cx="{(a[0] + b[0]) / 2}" cy="{(a[1] + b[1]) / 2}" '
                f'r="3" fill="white" stroke="{INK}" data-join-boundary="{boundary}"/>'
            )
    for i in indices:
        x, y = xy(i)
        tag = f' data-loop-index="{i}"' if ls <= i < le else ""
        rows.extend(
            [
                f'<circle cx="{x}" cy="{y}" r="8" fill="white"/>',
                f'<text x="{x}" y="{y + 5}" text-anchor="middle" '
                f'font-size="{nucleotide_font_size}" '
                f'data-base-index="{i}"{tag}>{escape(sequence[i])}</text>',
            ]
        )
    rows.extend(
        [
            '<text x="20" y="190" font-size="13">5\u2032 upper arm → loop → lower '
            "arm 3\u2032</text>",
            '<text x="20" y="211" font-size="12">Closing crop; nucleotide counts, '
            "not a physical loop radius.</text>",
            "</g></svg>",
        ]
    )
    return "\n".join(rows).encode()
