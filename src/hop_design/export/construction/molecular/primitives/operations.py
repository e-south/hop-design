"""Measured operation rows: a visible arrow and a name centered beside it."""

from xml.etree import ElementTree as ET

from .style import (
    ANNOTATION_SIZE,
    INK,
    OPERATION_ARROW_LENGTH,
    OPERATION_GAP,
    OPERATION_STROKE,
    SCENE_CLEARANCE,
)
from .typography import text_width

SVG = "http://www.w3.org/2000/svg"


def draw_operation(
    root: ET.Element, center: float, top: float, width: float, kind: str, label: str
) -> tuple[float, float]:
    y = top
    bottom = y + OPERATION_ARROW_LENGTH
    ET.SubElement(
        root,
        f"{{{SVG}}}path",
        {
            "d": f"M{center},{y} V{bottom - 22}",
            "stroke": INK,
            "stroke-width": str(OPERATION_STROKE),
            "fill": "none",
            "stroke-linecap": "round",
            "data-operation-arrow": "true",
            "data-drawing-box": f"{center - 14} {y} 28 {OPERATION_ARROW_LENGTH}",
        },
    )
    ET.SubElement(
        root,
        f"{{{SVG}}}path",
        {
            "d": f"M{center - 14},{bottom - 24} L{center},{bottom} L{center + 14},{bottom - 24} Z",
            "fill": INK,
            "data-operation-arrowhead": "true",
        },
    )
    x = center + OPERATION_GAP
    ET.SubElement(
        root,
        f"{{{SVG}}}text",
        {
            "x": str(x),
            "y": str(y + OPERATION_ARROW_LENGTH / 2 + ANNOTATION_SIZE * 0.35),
            "font-size": str(ANNOTATION_SIZE),
            "data-operation": kind,
        },
    ).text = label
    return max(width, x + text_width(label, ANNOTATION_SIZE) + 24), bottom + SCENE_CLEARANCE
