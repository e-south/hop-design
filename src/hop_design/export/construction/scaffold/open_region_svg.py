"""Aligned, countable open-side contacts from the existing exact hairpin portrait."""

from html import escape

from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..hairpin_svg import BLUE, GREY, INK


def open_region_fragment(
    portrait: HairpinPortraitProjection,
    reference: HairpinPortraitProjection,
    *,
    x: float,
    y: float,
    paired_window: int,
    pitch: float = 13,
) -> str:
    """Align by the supplied-stem boundary; do not perform a sequence alignment."""
    anchor = portrait.stem_primary_span.start.offset
    reference_anchor = reference.stem_primary_span.start.offset
    reference_pairs = {p.left_index - reference_anchor: p for p in reference.state.pairings}
    pairs = [p for p in portrait.state.pairings if -paired_window <= p.left_index - anchor < 2]
    rows = [f'<g data-region="open-side" data-state-id="{escape(portrait.state.state_id)}">']
    stem_x = x + paired_window * pitch
    rows.append(
        f'<path d="M{stem_x - pitch / 2},{y - 18} V{y + 54}" '
        f'stroke="{GREY}" stroke-dasharray="3 3" fill="none"/>'
    )
    for pair in pairs:
        relative = pair.left_index - anchor
        px = x + (relative + paired_window) * pitch
        other = reference_pairs.get(relative)
        color = GREY if relative >= 0 else BLUE
        if other is None:
            color = "#B96716"
        elif (pair.left_base, pair.right_base) != (other.left_base, other.right_base):
            color = "#8B4A89"
        for base, dy in ((pair.left_base, 0), (pair.right_base, 40)):
            rows.append(
                f'<text x="{px}" y="{y + dy}" font-size="14" text-anchor="middle" '
                f'fill="{color}" data-offset-from-stem="{relative}">{base}</text>'
            )
        dash = "" if pair.kind.value == "watson_crick" else ' stroke-dasharray="2 2"'
        rows.append(
            f'<line x1="{px}" x2="{px}" y1="{y + 6}" y2="{y + 24}" '
            f'stroke="{INK}" stroke-width="0.6"{dash}/>'
        )
    rows.append("</g>")
    return "\n".join(rows)
