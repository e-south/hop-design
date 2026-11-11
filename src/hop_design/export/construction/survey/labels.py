"""Shared measured labels for compact and wide parameter-coordinate figures."""

from typing import Any
from xml.etree import ElementTree as ET

from ..presentation.figure_profile import FigureProfile
from .axis_frame import AxisFrame
from .layout import compact_heading, heading_lines

SVG = "http://www.w3.org/2000/svg"


def headings(
    parent: ET.Element,
    axis: dict[str, Any],
    x: float,
    offset: float,
    frame: AxisFrame,
    profile: FigureProfile,
) -> None:
    unit = {"positions": "pos", "contacts": "ct"}.get(axis["unit"], axis["unit"])
    lines = heading_lines(axis, profile=profile)
    if profile.rotated_labels:
        label = compact_heading(axis)
        ET.SubElement(
            parent,
            f"{{{SVG}}}text",
            {
                "x": str(x),
                "y": str(offset + frame.heading_y + profile.axis_font * 0.35),
                "transform": f"rotate(-45 {x} {offset + frame.heading_y})",
                "text-anchor": "end",
                "font-weight": "normal",
                "fill": "#263b40",
                "data-heading-angle": "-45",
            },
        ).text = label
    else:
        for i, line in enumerate(lines):
            ET.SubElement(
                parent,
                f"{{{SVG}}}text",
                {
                    "x": str(x),
                    "y": str(offset + frame.heading_y + i * profile.axis_font),
                    "text-anchor": "middle",
                    "fill": "#263b40",
                },
            ).text = line
        ET.SubElement(
            parent,
            f"{{{SVG}}}text",
            {
                "x": str(x),
                "y": str(offset + frame.heading_y + 3 + len(lines) * profile.axis_font),
                "text-anchor": "middle",
                "fill": "#617277",
            },
        ).text = unit


def node_text(parent: ET.Element, x: float, y: float, geometry: dict[str, Any], font: int) -> None:
    lines = geometry["lines"]
    for j, line in enumerate(lines):
        attrs = {
            "x": str(x),
            "y": str(y + (j - (len(lines) - 1) / 2) * font + font * 0.35),
            "text-anchor": "middle",
            "fill": "#263b40",
            "data-node-label": "true",
        }
        if geometry.get("rotation"):
            attrs["transform"] = f"rotate({geometry['rotation']} {x} {y})"
        ET.SubElement(parent, f"{{{SVG}}}text", attrs).text = line
