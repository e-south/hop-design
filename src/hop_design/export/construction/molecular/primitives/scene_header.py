"""Attach a stage title to measured content without changing molecular coordinates."""

from xml.etree import ElementTree as ET

from .extent import scene_bounds
from .style import SCENE_CLEARANCE, TITLE_SIZE

SVG = "http://www.w3.org/2000/svg"


def attach_scene_header(root: ET.Element) -> None:
    title = next(e for e in root.iter() if e.get("data-stage-title"))
    for parent in root.iter():
        if title in list(parent):
            parent.remove(title)
            break
    content = ET.Element(f"{{{SVG}}}g", {"data-scene-content": "true"})
    content.extend(list(root))
    for child in list(root):
        root.remove(child)
    left, top, _, _ = scene_bounds(content)
    offset = TITLE_SIZE + SCENE_CLEARANCE - top
    content.set("transform", f"translate(0 {offset})")
    content.set("data-scene-y", str(offset))
    title.set("y", str(TITLE_SIZE))
    root.extend((title, content))
    centers = [
        float(next(t for t in e if t.tag.endswith("}text")).attrib["y"]) - 5
        for e in content.iter()
        if e.get("data-base-index") is not None
    ]
    root.set("data-scene-entry-x", str(left - 16))
    root.set("data-scene-entry-y", str((min(centers) + max(centers)) / 2 + offset))
