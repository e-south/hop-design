"""One authoritative primer silhouette for drawing, clearance and measurement."""

from math import hypot

from .ribbon import ribbon_points, rounded_path
from .style import INK

Point = tuple[float, float]
PRIMER_HALF_WIDTH = 12
PRIMER_HEAD_LENGTH = 32
PRIMER_SHOULDER_HEIGHT = 24
PRIMER_SHOULDER_ADVANCE = 8


def primer_outline(positions: list[Point], *, outward: int = 1) -> tuple[list[Point], int]:
    """One closed ribbon with an integrated directional wedge beyond the last base."""
    contour = ribbon_points(positions, PRIMER_HALF_WIDTH)
    split = len(contour) // 2
    x, y = positions[-1]
    px, py = positions[-2] if len(positions) > 1 else (x - 16, y)
    length = max(1, hypot(x - px, y - py))
    ux, uy = (x - px) / length, (y - py) / length
    # The template-facing edge continues flat to the tip. Only the outer edge
    # flares; mirroring the flare never reverses sequence or extension direction.
    nx, ny = -uy * outward, ux * outward
    shoulder = (
        x + ux * PRIMER_SHOULDER_ADVANCE + nx * PRIMER_SHOULDER_HEIGHT,
        y + uy * PRIMER_SHOULDER_ADVANCE + ny * PRIMER_SHOULDER_HEIGHT,
    )
    tip = (
        x + ux * PRIMER_HEAD_LENGTH - nx * PRIMER_HALF_WIDTH,
        y + uy * PRIMER_HEAD_LENGTH - ny * PRIMER_HALF_WIDTH,
    )
    wedge = [shoulder, tip] if outward > 0 else [tip, shoulder]
    outline = [*contour[:split], *wedge, *contour[split:]]
    tip_index = split + (1 if outward > 0 else 0)
    return outline, tip_index


def primer_contour(positions: list[Point], *, outward: int = 1) -> str:
    outline, tip_index = primer_outline(positions, outward=outward)
    path = rounded_path(outline, sharp=frozenset({tip_index}))
    return (
        f'<path data-primer-contour="true" data-primer-shape="integrated-wedge" '
        f'd="{path}" fill="#F2F4F5" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
    )


def outline_box(points: list[Point], padding: float = 2) -> tuple[float, float, float, float]:
    left, top = min(x for x, _ in points) - padding, min(y for _, y in points) - padding
    return (
        left,
        top,
        max(x for x, _ in points) + padding - left,
        max(y for _, y in points) + padding - top,
    )
