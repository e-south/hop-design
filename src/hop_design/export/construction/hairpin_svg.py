"""Draw recorded hairpin architecture without solving or predicting molecular state."""

from __future__ import annotations

from html import escape
from itertools import pairwise

from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from .scaffold.hairpin_layout import HairpinLayout

BLUE, GREEN, GREY, INK = "#176B9A", "#258365", "#9AA3AA", "#23313B"


def _text(
    x: float, y: float, value: str, *, size: int = 13, anchor: str = "start", color: str = INK
) -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" '
        f'text-anchor="{anchor}" fill="{color}">{escape(value)}</text>'
    )


def _bracket(x1: float, x2: float, y: float, label: str, color: str) -> str:
    return (
        f'<path d="M{x1:.2f},{y + 4} V{y} H{x2:.2f} V{y + 4}" fill="none" stroke="{color}"/>'
        + _text((x1 + x2) / 2, y - 7, label, anchor="middle", color=color)
    )


def render_hairpin_portrait_svg(p: HairpinPortraitProjection) -> bytes:
    """Render one exact, single-loop molecular portrait with staged interface detail."""
    strand = p.state.molecules[0]
    start, stop = p.stem_primary_span.start.offset, p.stem_primary_span.end.offset
    ls, le = p.loop_span.start.offset, p.loop_span.end.offset
    paired_start = p.paired_primary_span.start.offset
    layout = HairpinLayout(p)
    anchor, top, bottom = layout.anchor, 111.0, 145.0
    loop_x, radius = layout.loop_x, layout.radius
    width = max(800.0, loop_x + 210)
    point = layout.point

    def region(i: int) -> str:
        if p.stem_primary_span.contains_index(i) or p.stem_return_span.contains_index(i):
            return GREY
        if stop <= i < p.stem_return_span.start.offset:
            return GREEN
        return BLUE

    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width * 180 / 800:.2f}mm" '
        'height="94.5mm" '
        f'viewBox="0 0 {width:.1f} 420" role="img">',
        "<title>Choose a hairpin by its scaffold</title>",
        "<desc>Hairpin sequence and pairing. "
        "Exact selection and preparation accompany this view.</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        _text(28, 29, "Whole-hairpin design", size=19),
        _text(
            28,
            50,
            "Joined hairpin · "
            + (
                "requested endpoint"
                if p.stage_role == "endpoint"
                else "intermediate before copying"
            ),
        ),
        f'<g id="hairpin-shape" data-state-id="{escape(p.state.state_id)}">',
    ]
    points = [point(i) for i in range(len(strand.sequence))]
    for i, (a, b) in enumerate(pairwise(points)):
        segment = (
            f"A{radius:.2f},17 0 0 1 {b[0]:.2f},{b[1]:.2f}"
            if ls - 1 <= i < le
            else f"L{b[0]:.2f},{b[1]:.2f}"
        )
        rows.append(
            f'<path d="M{a[0]:.2f},{a[1]:.2f} {segment}" '
            f'stroke="{region(i)}" stroke-width="2.6" fill="none" data-backbone-index="{i}"/>'
        )
    for pair in p.ordered_contacts:
        a, b = points[pair.left_index], points[pair.right_index]
        dash = "" if pair.kind.value == "watson_crick" else ' stroke-dasharray="2 2"'
        rows.append(
            f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" '
            f'stroke="{region(pair.left_index)}" stroke-width="1"{dash} '
            f'data-pair-left-index="{pair.left_index}" '
            f'data-pair-right-index="{pair.right_index}" data-pair-kind="{pair.kind.value}"/>'
        )
    for boundary in p.join_boundaries:
        a, b = points[boundary - 1], points[boundary]
        rows.append(
            f'<circle cx="{(a[0] + b[0]) / 2:.2f}" cy="{(a[1] + b[1]) / 2:.2f}" '
            f'r="3.2" fill="white" stroke="{INK}" data-join-boundary="{boundary}"/>'
        )
    rows += [
        _text(points[0][0] - 8, top + 4, "5\u2032", anchor="end"),
        _text(points[-1][0] - 8, bottom + 4, "3\u2032", anchor="end"),
        _bracket(
            point(paired_start)[0] - 2,
            anchor - 3,
            90,
            f"{p.open_side_paired_positions} open-side positions",
            BLUE,
        ),
        _bracket(anchor, point(stop - 1)[0], 176, f"{p.stem_bp}-bp supplied stem", GREY),
        _bracket(
            point(stop)[0] - 2,
            point(ls - 1)[0] + 2,
            90,
            f"{p.loop_side_paired_bp} loop-side bp",
            GREEN,
        ),
        _text(loop_x + radius + 13, 124, f"{p.loop_nt}-nt loop", color=GREEN),
        "</g>",
        _text(
            28,
            215,
            "Open-side detail"
            if p.open_side_paired_positions <= 18
            else "Open-side detail: 18 positions nearest stem",
            size=15,
        ),
    ]
    # Actual contacts nearest the supplied stem; cap the crop rather than shrink bases.
    crop = sorted(
        (pair for pair in p.ordered_contacts if pair.left_index < start),
        key=lambda pair: pair.left_index,
    )[-18:]
    for j, pair in enumerate(crop):
        x = 38 + j * 17
        rows += [
            _text(x, 243, pair.left_base, anchor="middle", color=BLUE),
            _text(x, 279, pair.right_base, anchor="middle", color=BLUE),
            _text(x, 262, "│" if pair.kind.value == "watson_crick" else "·", anchor="middle"),
        ]
    rows += [
        _text(
            28,
            301,
            f"5\u2032 {strand.five_prime_end.value} · 3\u2032 {strand.three_prime_end.value}",
        ),
        _text(
            28,
            320,
            f"Unpaired terminal tracts: 5\u2032 {p.five_prime_unpaired_nt} / "
            f"3\u2032 {p.three_prime_unpaired_nt} nt",
        ),
        _text(28, 339, f"Noncanonical open-side contacts: {p.noncanonical_open_side_contacts}"),
        _text(420, 215, "Closing detail", size=15, color=GREEN),
        _text(420, 242, f"Loop: 5\u2032 {strand.sequence[ls:le]} 3\u2032", color=GREEN),
        _text(420, 266, "○ recorded covalent join · │ canonical contact"),
    ]
    if p.later_release is not None:
        rows.append('<g data-stage="clone_ready_duplex">')
        rows.append(_text(420, 294, "After copying and release", size=14))
        for i, end in enumerate(p.later_release.cohesive_ends):
            polarity = "5\u2032" if end.overhang_end.value == "five_prime" else "3\u2032"
            rows.append(
                _text(
                    420,
                    316 + i * 21,
                    f"{end.product_end}: 5\u2032 {end.sequence} 3\u2032 · {polarity} overhang",
                )
            )
        rows.append("</g>")
    else:
        rows.append(_text(420, 302, "No downstream release interface requested."))
    rows += [
        _text(
            28,
            395,
            "Selection and exact materials: selection.json → preparation/oligos.csv",
            size=12,
        ),
        "</g></svg>",
    ]
    return ("\n".join(rows) + "\n").encode()


__all__ = ["render_hairpin_portrait_svg"]
