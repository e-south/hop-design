"""Place a recorded joining mark outside its local molecular backbone."""

from html import escape
from math import hypot

from hop_design.models.construction.projections.inspection import MolecularStateInspection
from hop_design.models.construction.projections.inspection_annotations import InspectionBoundary

from .style import INK

Point = tuple[float, float]


def bond_bridge(
    projection: MolecularStateInspection,
    points: dict[tuple[str, int], Point],
    join: InspectionBoundary,
) -> tuple[str, tuple[float, float, float, float]]:
    if join.before is None or join.after is None:
        raise ValueError("A formed bond requires both recorded adjacent bases.")
    a = points[join.before.strand_id, join.before.index]
    b = points[join.after.strand_id, join.after.index]
    x, y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    length = max(hypot(b[0] - a[0], b[1] - a[1]), 1e-9)
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    nx, ny = -uy, ux
    centers = []
    for pair in projection.state.pairings:
        paired_left = points[pair.left_strand_id, pair.left_index]
        paired_right = points[pair.right_strand_id, pair.right_index]
        centers.append(
            ((paired_left[0] + paired_right[0]) / 2, (paired_left[1] + paired_right[1]) / 2)
        )
    if centers:
        cx, cy = min(centers, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
    else:
        cx = sum(p[0] for p in points.values()) / len(points)
        cy = sum(p[1] for p in points.values()) / len(points)
    if nx * (x - cx) + ny * (y - cy) < 0:
        nx, ny = -nx, -ny

    def point(along: float, outward: float) -> Point:
        return x + ux * along + nx * outward, y + uy * along + ny * outward

    stem = [point(0, 14), point(0, 34)]
    staple = [point(-12, 19), point(-12, 34), point(12, 34), point(12, 19)]
    contour = [*stem, *staple]
    left, top = min(p[0] for p in contour) - 3, min(p[1] for p in contour) - 3
    box = left, top, max(p[0] for p in contour) + 3 - left, max(p[1] for p in contour) + 3 - top

    def path(ps: list[Point]) -> str:
        return " ".join(f"{'M' if i == 0 else 'L'}{a},{b}" for i, (a, b) in enumerate(ps))

    drawing = (
        f'<g data-formed-bond="{join.after.index}" data-event-glyph="bond-bridge" '
        f'data-bond-strand="{escape(join.after.strand_id)}" '
        f'data-bond-point="{x} {y}" data-bond-outward="{nx} {ny}" '
        f'data-drawing-box="{" ".join(map(str, box))}">'
        "<title>Recorded ligation bond</title>"
        f'<path d="{path(stem)}" stroke="{INK}" stroke-width="1.8"/>'
        f'<path d="{path(staple)}" fill="none" stroke="{INK}" stroke-width="3.2" '
        'stroke-linejoin="round"/></g>'
    )
    return drawing, box
