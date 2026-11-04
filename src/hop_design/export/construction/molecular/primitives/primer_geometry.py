"""Parallel input glyphs; their bases annotate an input, not a paired state."""

from collections import defaultdict
from itertools import pairwise
from math import floor, hypot

Point = tuple[float, float]


def outward_side(points: list[Point], center: Point) -> int:
    # Orient at the handle's entrance. Its later bend and the distant stem must
    # not flip which side of that entrance is outside the molecule.
    following = points[1] if len(points) > 1 else (points[0][0] + 1, points[0][1])
    dx, dy = following[0] - points[0][0], following[1] - points[0][1]
    x = sum(p[0] for p in points) / len(points) - center[0]
    y = sum(p[1] for p in points) / len(points) - center[1]
    return 1 if -dy * x + dx * y >= 0 else -1


def parallel_positions(points: list[Point], distance: float) -> list[Point]:
    """Offset a handle's segments normally, then space its input letters evenly.

    Offset segment intersections keep one clearance through a bend. Resampling
    avoids overlapping letters near an inside corner; it changes no binding
    interval or molecular coordinates.
    """
    if len(points) == 1:
        return [(points[0][0], points[0][1] + distance)]
    corners = [points[0]]
    for a, b, c in zip(points, points[1:], points[2:], strict=False):
        u, v = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
        if abs(u[0] * v[1] - u[1] * v[0]) > 1e-6:
            corners.append(b)
    corners.append(points[-1])
    normals = []
    for a, b in pairwise(corners):
        length = max(hypot(b[0] - a[0], b[1] - a[1]), 1e-9)
        normals.append((-(b[1] - a[1]) / length, (b[0] - a[0]) / length))
    offset = []
    for i, (x, y) in enumerate(corners):
        a, b = normals[max(0, i - 1)], normals[min(i, len(normals) - 1)]
        denominator = max(0.5, 1 + a[0] * b[0] + a[1] * b[1])
        offset.append(
            (x + (a[0] + b[0]) * distance / denominator, y + (a[1] + b[1]) * distance / denominator)
        )
    lengths = [hypot(b[0] - a[0], b[1] - a[1]) for a, b in pairwise(offset)]
    total = sum(lengths)
    result = []
    for i in range(len(points)):
        remaining = total * i / (len(points) - 1)
        for j, length in enumerate(lengths):
            if remaining <= length or j == len(lengths) - 1:
                t = remaining / max(length, 1e-9)
                a, b = offset[j : j + 2]
                result.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                break
            remaining -= length
    return result


def position_primer(
    template: list[Point], molecule: list[Point], *, outward: int, leading: int = 0
) -> list[Point]:
    """Find the nearest normal offset clearing the complete directional outline.

    Sample the outline, including its wedge, against the recorded base centers.
    A 23-unit exclusion radius covers a 13-unit strand half-width, half-pitch
    between adjacent bases and visible separation. This changes input placement
    only; template addresses, sequence order and extension direction stay fixed.
    If nearby lanes are occupied, translate the preferred silhouette beyond the
    scene's outward boundary instead of rejecting a valid molecular preparation.
    """
    from .primer_shape import primer_outline
    from .style import PRIMER_CLEARANCE

    # Invocation-local spatial bins retain the exact exclusion test while
    # avoiding a scan of the whole molecule for every outline sample.
    bins: dict[tuple[int, int], list[Point]] = defaultdict(list)
    for x, y in molecule:
        bins[floor(x / 23), floor(y / 23)].append((x, y))

    def clear(x: float, y: float) -> bool:
        i, j = floor(x / 23), floor(y / 23)
        return all(
            (x - a) ** 2 + (y - b) ** 2 >= 23**2
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for a, b in bins.get((i + dx, j + dy), ())
        )

    preferred: list[Point] = []
    for offset in range(0, 65, 2):
        positions = parallel_positions(template, outward * (PRIMER_CLEARANCE + offset))
        a, b = (
            positions[:2]
            if len(positions) > 1
            else (positions[0], (positions[0][0] + 16, positions[0][1]))
        )
        length = max(1, hypot(b[0] - a[0], b[1] - a[1]))
        positions = [
            (a[0] - (b[0] - a[0]) / length * 16 * i, a[1] - (b[1] - a[1]) / length * 16 * i)
            for i in reversed(range(1, leading + 1))
        ] + positions
        if offset == 0:
            preferred = positions
        outline, _ = primer_outline(positions, outward=outward)
        samples: list[Point] = []
        for a, b in pairwise([*outline, outline[0]]):
            steps = max(1, int(hypot(b[0] - a[0], b[1] - a[1]) / 4) + 1)
            samples.extend(
                (a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps)
                for i in range(steps)
            )
        if all(clear(x, y) for x, y in samples):
            return positions
    # A separating half-plane guarantees clearance for the entire polygon, not
    # only its sampled edges. One rigid translation preserves bends and lettering.
    a, b = (
        template[:2] if len(template) > 1 else (template[0], (template[0][0] + 16, template[0][1]))
    )
    length = max(1, hypot(b[0] - a[0], b[1] - a[1]))
    nx, ny = -(b[1] - a[1]) * outward / length, (b[0] - a[0]) * outward / length
    outline, _ = primer_outline(preferred, outward=outward)
    shift = max(
        0, max(x * nx + y * ny for x, y in molecule) + 24 - min(x * nx + y * ny for x, y in outline)
    )
    return [(x + nx * shift, y + ny * shift) for x, y in preferred]
