"""Measure native scene content without accumulating standalone page margins."""

import json
from collections.abc import Iterator
from xml.etree import ElementTree as ET

from .style import SCENE_CLEARANCE
from .typography import text_width


def scene_bounds(root: ET.Element) -> tuple[float, float, float, float]:
    """Include exact base boxes, input arrows and collision-placed annotations."""
    left, top, right, bottom = float("inf"), float("inf"), 0.0, 0.0

    def nodes(element: ET.Element, y: float = 0) -> Iterator[tuple[ET.Element, float]]:
        y += float(element.get("data-scene-y", "0"))
        yield element, y
        for child in element:
            yield from nodes(child, y)

    for node, offset_y in nodes(root):
        box = None
        if node.get("data-label-box"):
            box = json.loads(node.attrib["data-label-box"])
        elif node.get("data-drawing-box"):
            box = [float(v) for v in node.attrib["data-drawing-box"].split()]
        elif node.get("data-base-index") is not None:
            rect = next(e for e in node if e.tag.endswith("}rect"))
            box = [float(rect.attrib[k]) for k in ("x", "y", "width", "height")]
            # Boundary and recognition marks can extend beyond the base tile.
            box = [box[0] - 14, box[1] - 14, box[2] + 28, box[3] + 28]
        elif node.tag.endswith("}text") and not node.get("data-caption") and node.text:
            size = float(node.get("font-size", "16"))
            width = text_width(node.text, size, bold=node.get("font-weight") == "600")
            x = float(node.get("x", "0"))
            anchor = node.get("text-anchor")
            x -= width / 2 if anchor == "middle" else width if anchor == "end" else 0
            box = [x, float(node.get("y", "0")) - size, width, size + 5]
        if box:
            x, y, width, height = box
            y += offset_y
            left, top = min(left, x), min(top, y)
            right, bottom = max(right, x + width), max(bottom, y + height)
    return (left, top, right - left, bottom - top) if left != float("inf") else (0, 0, 0, 0)


def scene_extent(root: ET.Element) -> tuple[float, float]:
    left, top, width, height = scene_bounds(root)
    return left + width + SCENE_CLEARANCE, top + height + SCENE_CLEARANCE
