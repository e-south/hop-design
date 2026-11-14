"""Keep redundant terminal ink clear of recorded reference fragments and fold cues."""

import json
from xml.etree import ElementTree as ET

SVG = "{http://www.w3.org/2000/svg}"


def avoid_reference_label_collisions(root: ET.Element) -> None:
    """Suppress only colliding terminal ink; retain its exact address and chemistry."""
    obstacles: list[tuple[float, ...]] = []
    for item in root.iter():
        if item.get("data-ghost-base-index") is not None:
            text = next(item.iter(SVG + "text"))
            obstacles.append((float(text.attrib["x"]) - 9, float(text.attrib["y"]) - 19, 18, 28))
        if item.get("data-foldback-cue") and item.get("data-drawing-box"):
            obstacles.append(tuple(map(float, item.attrib["data-drawing-box"].split())))
    for item in root.iter(SVG + "text"):
        if item.get("data-label-kind") != "terminus" or not item.get("data-label-box"):
            continue
        x, y, w, h = json.loads(item.attrib["data-label-box"])
        if not any(x < a + c and a < x + w and y < b + d and b < y + h for a, b, c, d in obstacles):
            continue
        item.tag = SVG + "g"
        item.text = None
        for key in list(item.attrib):
            if not key.startswith("data-terminal-"):
                del item.attrib[key]
        item.set("data-terminal-display", "metadata")
        if not any(child.tag == SVG + "title" for child in item):
            ET.SubElement(item, SVG + "title").text = item.attrib["data-terminal-chemistry"]
