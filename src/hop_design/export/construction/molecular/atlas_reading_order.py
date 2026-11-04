"""Reading-order cue shared by route and page composition."""

from .atlas_placement import RoutePlacement
from .primitives.style import INK


def continuation_svg(
    placement: RoutePlacement,
    start: tuple[float, float] | None = None,
    end: tuple[float, float] | None = None,
) -> str:
    if placement.continuation is None:
        return ""
    x, y, target, top = placement.continuation
    bottom, right, end_y, radius = y + 24, target - 48, top + 100, 20
    if end is not None:
        target, end_y = end
    x, source_y = start if start is not None else (x, y)
    first_radius = min(radius, (bottom - source_y) / 2)
    return (
        f'<g xmlns="http://www.w3.org/2000/svg" data-column-continuation="true">'
        f'<path d="M{x},{source_y} V{bottom - first_radius} '
        f"Q{x},{bottom} {x + first_radius},{bottom} H{right - radius} "
        f"Q{right},{bottom} {right},{bottom - radius} V{end_y + radius} "
        f'Q{right},{end_y} {right + radius},{end_y} H{target - 16}" '
        f'stroke="{INK}" fill="none" stroke-width="3" stroke-opacity=".65" stroke-linecap="round"/>'
        f'<path d="M{target - 18},{end_y - 10} L{target},{end_y} '
        f'L{target - 18},{end_y + 10} Z" fill="{INK}" fill-opacity=".65"/></g>'
    )
