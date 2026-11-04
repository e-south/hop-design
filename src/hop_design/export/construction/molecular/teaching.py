"""Exact selected teaching scenes, reflowed at the route's nucleotide type size."""

import json
from typing import Any
from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.atlas import AtlasComparison, MolecularAtlas

from .atlas_blocks import route_blocks
from .printing.panels import scene_panels
from .teaching_annotations import teaching_brackets

SVG = "http://www.w3.org/2000/svg"
WIDTH = 1008.0  # Seven inches at half a point per native unit: 16-unit bases = 8 pt.
MARGIN = 24.0


def render_parameter_teaching(
    teaching: dict[str, Any],
    atlas: MolecularAtlas,
    locations: list[dict[str, Any]],
    *,
    comparison: AtlasComparison | None = None,
) -> bytes:
    """Use the selected atlas directly; wrapping changes presentation, never strands."""
    if teaching["materialized_realization_id"] != atlas.materialized_realization_id:
        raise ValueError("Teaching and atlas must describe the same preparation.")
    scenes = teaching["scenes"]
    wanted = {s["state_id"] for s in scenes}
    selected = atlas.model_copy(
        update={
            "states": tuple(s for s in atlas.states if s.state.state_id in wanted),
            "transitions": (),
            "inputs": (),  # Primer entry and binding belong to the chronological route.
        }
    )
    blocks = {
        b.element.attrib["data-atlas-state"]: b
        for b in route_blocks(selected, comparison, locations)
    }
    root = ET.Element(
        f"{{{SVG}}}svg",
        {
            "viewBox": f"0 0 {WIDTH} 1",
            "width": "7in",
            "role": "img",
            "aria-label": "Exact molecular measurements for the selected preparation",
            "font-family": "Arial, Helvetica, sans-serif",
            "fill": "#243740",
            "data-preparation-id": atlas.materialized_realization_id,
            "data-teaching-resolution": "every-base",
        },
    )
    ET.SubElement(root, f"{{{SVG}}}rect", width="100%", height="100%", fill="white")
    definitions = ET.SubElement(root, f"{{{SVG}}}defs")
    y = 12.0
    for frame in teaching["frames"]:
        frame_scenes = [s for s in scenes if s["frame"] == frame["key"]]
        if not frame_scenes:
            continue
        group = ET.SubElement(root, f"{{{SVG}}}g", {"data-teaching-frame": frame["key"]})
        for scene in frame_scenes:
            row = blocks[scene["state_id"]].element
            title = next(e for e in row.iter() if e.get("data-stage-title"))
            title.text = scene["title"]
            for feature in row.iter():
                if (
                    feature.get("data-site-id")
                    and feature.get("data-parameter-keys")
                    and any(child.get("data-recognition-footprint") for child in feature)
                ):
                    feature.set("data-teaching-keys", feature.attrib["data-parameter-keys"])
            teaching_brackets(row, teaching, locations)
            for panel in scene_panels(row, WIDTH - 2 * MARGIN):
                placed = ET.SubElement(group, f"{{{SVG}}}g", transform=f"translate({MARGIN} {y})")
                for parent in panel.element.iter():
                    for child in list(parent):
                        if child.tag == f"{{{SVG}}}defs":
                            definitions.extend(child)
                            parent.remove(child)
                placed.append(panel.element)
                placed.set("data-teaching-continuation", json.dumps(panel.description))
                placed.set("data-panel-height", str(panel.height))
                y += panel.height + 24
    # Keep the complete vocabulary inspectable without invisible focus targets.
    ET.SubElement(
        root, f"{{{SVG}}}metadata", {"data-teaching-parameters": "true"}
    ).text = json.dumps(teaching["parameters"])
    root.set("viewBox", f"0 0 {WIDTH} {y}")
    root.set("height", f"{y / 2}pt")
    return bytes(ET.tostring(root, encoding="utf-8"))
