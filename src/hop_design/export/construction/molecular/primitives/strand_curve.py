"""Continuous region ink through nucleotide centers, with shared half-base borders."""

from math import hypot

Point = tuple[float, float]
Curve = tuple[Point, Point, Point, Point]


def _mix(a: Point, b: Point, t: float) -> Point:
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def _halves(curve: Curve) -> tuple[Curve, Curve]:
    a, b, c, d = curve
    ab, bc, cd = _mix(a, b, 0.5), _mix(b, c, 0.5), _mix(c, d, 0.5)
    abc, bcd = _mix(ab, bc, 0.5), _mix(bc, cd, 0.5)
    middle = _mix(abc, bcd, 0.5)
    return (a, ab, abc, middle), (middle, bcd, cd, d)


def _line(a: Point, b: Point) -> Curve:
    return a, _mix(a, b, 1 / 3), _mix(a, b, 2 / 3), b


def band_segments(
    points: list[Point], start: int, end: int, *, terminal_extension: float = 6
) -> list[Curve]:
    """Curves pass through every base; neighboring regions share one boundary.

    Context includes up to two neighboring bases on each side. Strand endpoints
    extend six drawing units, leaving a visible gap at adjacent strand breaks.
    This changes ink only, never base coordinates.
    """
    if not 0 <= start <= end < len(points):
        raise ValueError("A region requires an in-bounds ordered base interval.")
    if len(points) == 1:
        x, y = points[0]
        return [_line((x - terminal_extension, y), (x + terminal_extension, y))]
    first, second = points[:2]
    penultimate, last = points[-2:]
    context = [_mix(second, first, 2), *points, _mix(penultimate, last, 2)]
    segments = []
    if start == 0:
        length = max(hypot(second[0] - first[0], second[1] - first[1]), 1e-9)
        segments.append(_line(_mix(first, second, -terminal_extension / length), first))
    for index in range(max(0, start - 1), min(end + 1, len(points) - 1)):
        a, b, c, d = context[index : index + 4]
        curve = (
            b,
            (b[0] + (c[0] - a[0]) / 6, b[1] + (c[1] - a[1]) / 6),
            (c[0] - (d[0] - b[0]) / 6, c[1] - (d[1] - b[1]) / 6),
            c,
        )
        if index < start:
            curve = _halves(curve)[1]
        elif index == end:
            curve = _halves(curve)[0]
        segments.append(curve)
    if end == len(points) - 1:
        length = max(hypot(last[0] - penultimate[0], last[1] - penultimate[1]), 1e-9)
        segments.append(_line(last, _mix(last, penultimate, -terminal_extension / length)))
    return segments


def band_path(points: list[Point], start: int, end: int) -> str:
    segments = band_segments(points, start, end)

    def xy(point: Point) -> str:
        return f"{point[0]:.4f},{point[1]:.4f}"

    return (
        "M"
        + xy(segments[0][0])
        + " ".join("C" + " ".join(map(xy, curve[1:])) for curve in segments)
    )
