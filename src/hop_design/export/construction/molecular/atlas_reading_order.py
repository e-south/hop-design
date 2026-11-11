"""Reading-order cue shared by route and page composition."""

from typing import Literal

from .atlas_placement import RoutePlacement
from .primitives.style import INK, OPERATION_STROKE


def continuation_svg(
    placement: RoutePlacement,
    start: tuple[float, float] | None = None,
    end: tuple[float, float] | None = None,
    *,
    from_side: bool = False,
    side_origin: Literal["loop-cap", "retained-foldback"] = "loop-cap",
) -> str:
    if placement.continuation is None:
        return ""
    x, y, target, top = placement.continuation
    bottom, right, end_y, radius = y + 24, target - 48, top + 100, 20.0
    if end is not None:
        target, end_y = end
    x, source_y = start if start is not None else (x, y)
    first_radius = min(radius, (bottom - source_y) / 2)
    if from_side:
        # Leave the exposed foldback region or cap horizontally into the gutter.
        radius = min(48, (target - x - 24) / 3, (source_y - end_y) / 2)
        if radius <= 0:
            raise ValueError(
                "A side continuation requires positive horizontal and upward clearance."
            )
        right = target - radius - 24
        path = (
            f"M{x},{source_y} H{right - radius} "
            f"Q{right},{source_y} {right},{source_y - radius} V{end_y + radius} "
            f"Q{right},{end_y} {right + radius},{end_y} H{target - 16}"
        )
    else:
        path = (
            f"M{x},{source_y} V{bottom - first_radius} "
            f"Q{x},{bottom} {x + first_radius},{bottom} H{right - radius} "
            f"Q{right},{bottom} {right},{bottom - radius} V{end_y + radius} "
            f"Q{right},{end_y} {right + radius},{end_y} H{target - 16}"
        )
    return (
        f'<g xmlns="http://www.w3.org/2000/svg" data-column-continuation="true" '
        f'data-continuation-start="{side_origin if from_side else "operation"}">'
        f'<path d="{path}" '
        f'stroke="{INK}" fill="none" stroke-width="{OPERATION_STROKE}" stroke-linecap="round"/>'
        f'<path d="M{target - 18},{end_y - 10} L{target},{end_y} '
        f'L{target - 18},{end_y + 10} Z" fill="{INK}"/></g>'
    )
