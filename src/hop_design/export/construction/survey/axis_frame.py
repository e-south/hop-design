"""Measured vertical space for region names, axis headings and value contours."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AxisFrame:
    region_baseline: float
    region_height: float
    heading_y: float
    top: float
    bottom: float
    height: float


def measured_frame(*, font: int, heading_rows: int, node_rows: int, region_rows: int) -> AxisFrame:
    """Keep full text/box bounds apart, with one shared range across the cohort."""
    region_height = region_rows * font + 8
    heading_y = max(66, 4 + region_height + font + 8)
    unit_baseline = heading_y + 3 + heading_rows * font
    node_half_height = (node_rows * font + 4) / 2
    top = max(150, unit_baseline + font * 0.25 + 8 + node_half_height)
    bottom = top + max(150, 6 * font)
    return AxisFrame(
        region_baseline=4 + font,
        region_height=region_height,
        heading_y=heading_y,
        top=top,
        bottom=bottom,
        height=bottom + node_half_height + 8,
    )
