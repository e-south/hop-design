"""Constant-width recognition contours sampled from the shared strand curve."""

from math import hypot

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
