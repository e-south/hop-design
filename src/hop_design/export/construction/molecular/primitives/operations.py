"""Measured operation rows: a visible arrow and a name centered beside it."""

from xml.etree import ElementTree as ET

from .extent import scene_bounds
from .style import (
    ANNOTATION_SIZE,
    INK,
    OPERATION_ARROW_LENGTH,
    OPERATION_GAP,
    OPERATION_LABEL_INK,
    OPERATION_STROKE,
    SCENE_CLEARANCE,
)
from .typography import text_width

SVG = "http://www.w3.org/2000/svg"


def center_operation(root: ET.Element, next_title_top: float) -> None:
    """Use adjacent visible boundaries, including the next title's headroom.

    The operation may occupy otherwise empty headroom in the following scene;
    it remains separate from that scene's molecular content. Explicit input
    lists retain their existing operation/input reading order.
    """
    if any(e.get("data-atlas-input") for e in root.iter()):
        return
    scene = next(e for e in root if e.get("data-scene-content"))
    arrow = next(e for e in root if e.get("data-operation-arrow"))
    x, _, width, _ = map(float, arrow.attrib["data-drawing-box"].split())
    label = next(e for e in root if e.get("data-operation"))
    right = float(label.attrib["x"]) + text_width(label.text or "", ANNOTATION_SIZE)
    _, top, _, height = scene_bounds(scene, horizontal_span=(x, max(x + width, right)))
    bottom = top + height
    clearance = (next_title_top - bottom - OPERATION_ARROW_LENGTH) / 2
    if clearance < SCENE_CLEARANCE - 1e-7:
        raise ValueError("An operation requires clearance between content and the next title.")
    y = bottom + clearance
    end = y + OPERATION_ARROW_LENGTH
    center = x + width / 2
    arrow.set("d", f"M{center},{y} V{end - 22}")
    arrow.set("data-drawing-box", f"{x} {y} {width} {OPERATION_ARROW_LENGTH}")
    head = next(e for e in root if e.get("data-operation-arrowhead"))
    head.set("d", f"M{center - 14},{end - 24} L{center},{end} L{center + 14},{end - 24} Z")
    label.set("y", str(y + OPERATION_ARROW_LENGTH / 2 + ANNOTATION_SIZE * 0.35))


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
            "fill": OPERATION_LABEL_INK,
        },
    ).text = label
    return max(width, x + text_width(label, ANNOTATION_SIZE) + 24), bottom + SCENE_CLEARANCE
