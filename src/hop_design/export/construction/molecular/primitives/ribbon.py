"""Constant-width recognition contours sampled from the shared strand curve."""

from math import floor, hypot

from .strand_curve import band_segments


def ribbon_points(
    points: list[tuple[float, float]],
    half_width: float,
    start: int = 0,
    end: int | None = None,
    *,
    terminal_extension: float = 8,
) -> list[tuple[float, float]]:
    """Offset the same cubic centerline as region ink; keep exact half-base limits."""
    curves = band_segments(
        points,
        start,
        len(points) - 1 if end is None else end,
        terminal_extension=terminal_extension,
    )
    left, right = [], []
    for ordinal, (a, b, c, d) in enumerate(curves):
        for step in range(0 if ordinal == 0 else 1, 5):
            t = step / 4
            u = 1 - t
            x, y = (
                u**3 * a[k] + 3 * u * u * t * b[k] + 3 * u * t * t * c[k] + t**3 * d[k]
                for k in (0, 1)
            )
            dx, dy = (
                3 * u * u * (b[k] - a[k]) + 6 * u * t * (c[k] - b[k]) + 3 * t * t * (d[k] - c[k])
                for k in (0, 1)
            )
            length = max(hypot(dx, dy), 1e-9)
            nx, ny = -dy * half_width / length, dx * half_width / length
            left.append((x + nx, y + ny))
            right.append((x - nx, y - ny))
    return [*left, *reversed(right)]


def rounded_path(
    points: list[tuple[float, float]], radius: float = 2, *, sharp: frozenset[int] = frozenset()
) -> str:
    """Shallow corner rounding contained inside the original polygon."""
    original = points
    points = simple_outline(points)
    sharp = frozenset(i for i, p in enumerate(points) if any(p == original[j] for j in sharp))
    rows = []
    for i, (x, y) in enumerate(points):
        previous, following = points[i - 1], points[(i + 1) % len(points)]
        before, after = (
            hypot(previous[0] - x, previous[1] - y),
            hypot(following[0] - x, following[1] - y),
        )
        trim = 0 if i in sharp else min(radius, before / 2, after / 2)
        a = (
            x + (previous[0] - x) * trim / max(before, 1e-9),
            y + (previous[1] - y) * trim / max(before, 1e-9),
        )
        b = (
            x + (following[0] - x) * trim / max(after, 1e-9),
            y + (following[1] - y) * trim / max(after, 1e-9),
        )
        rows.append(f"{'M' if i == 0 else 'L'}{a[0]:.4f},{a[1]:.4f}")
        if trim:
            rows.append(f"Q{x:.4f},{y:.4f} {b[0]:.4f},{b[1]:.4f}")
    return " ".join(rows) + " Z"


def ribbon_path(
    points: list[tuple[float, float]],
    half_width: float,
    start: int = 0,
    end: int | None = None,
    *,
    terminal_extension: float = 8,
) -> str:
    outline = ribbon_points(points, half_width, start, end, terminal_extension=terminal_extension)
    n = len(outline) // 2
    # Internal color boundaries stay square so adjacent regions share a seam.
    sharp: set[int] = set()
    if start:
        sharp.update((0, len(outline) - 1))
    if end is not None and end < len(points) - 1:
        sharp.update((n - 1, n))
    return rounded_path(outline, sharp=frozenset(sharp))


def simple_outline(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Remove small offset loops at tight bends, retaining the enclosing contour."""

    def area(poly: list[tuple[float, float]]) -> float:
        return abs(
            sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, [*poly[1:], poly[0]], strict=True))
        )

    result = points
    for _ in range(len(points)):
        bins: dict[tuple[int, int], list[int]] = {}
        crossing = None
        for j, c in enumerate(result):
            d = result[(j + 1) % len(result)]
            cells = [
                (x, y)
                for x in range(floor(min(c[0], d[0]) / 64), floor(max(c[0], d[0]) / 64) + 1)
                for y in range(floor(min(c[1], d[1]) / 64), floor(max(c[1], d[1]) / 64) + 1)
            ]
            for i in sorted({i for cell in cells for i in bins.get(cell, ())}):
                if j - i <= 1 or (i == 0 and j == len(result) - 1):
                    continue
                a, b = result[i : i + 2]
                if (
                    max(a[0], b[0]) < min(c[0], d[0])
                    or min(a[0], b[0]) > max(c[0], d[0])
                    or max(a[1], b[1]) < min(c[1], d[1])
                    or min(a[1], b[1]) > max(c[1], d[1])
                ):
                    continue
                u, v = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1])
                denominator = u[0] * v[1] - u[1] * v[0]
                if abs(denominator) < 1e-9:
                    continue
                t = ((c[0] - a[0]) * v[1] - (c[1] - a[1]) * v[0]) / denominator
                q = ((c[0] - a[0]) * u[1] - (c[1] - a[1]) * u[0]) / denominator
                if 1e-7 < t < 1 - 1e-7 and 1e-7 < q < 1 - 1e-7:
                    crossing = (i, j, (a[0] + t * u[0], a[1] + t * u[1]))
                    break
            if crossing:
                break
            for cell in cells:
                bins.setdefault(cell, []).append(j)
        if crossing is None:
            break
        i, j, p = crossing
        result = max(
            ([p, *result[i + 1 : j + 1]], [p, *result[j + 1 :], *result[: i + 1]]), key=area
        )
    return result


def footprint_envelope(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Rounded-envelope vertices around the actual or lineage-bound duplex rows."""
    corners = sorted({(x + dx, y + dy) for x, y in points for dx in (-8, 8) for dy in (-18, 18)})

    def cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    sides = []
    for values in (corners, list(reversed(corners))):
        side: list[tuple[float, float]] = []
        for p in values:
            while len(side) >= 2 and cross(side[-2], side[-1], p) <= 0:
                side.pop()
            side.append(p)
        sides.extend(side[:-1])
    return sides
