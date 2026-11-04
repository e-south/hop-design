"""Publication-width pages from native scenes, with explicit coordinate continuations."""

import json
import math
from copy import deepcopy
from textwrap import wrap
from typing import Any
from xml.etree import ElementTree as ET

from ...presentation.print_contract import PrintContract
from ..atlas_placement import BlockExtent, place_route
from ..primitives.annotation_policy import draw_site_key
from ..primitives.style import ANNOTATION_SIZE
from .panels import ScenePanel, scene_panels

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
MARGIN = 24.0
# Continuation cues and feature labels use the shared minimum. Longer prose
# uses larger type without overstating the minimum across the complete page.
PUBLICATION = PrintContract(stage_title_pt=16)
PROSE_SIZE_PT = 12


def _extent(row: ET.Element) -> BlockExtent:
    values = [float(row.attrib[f"data-atlas-{k}"]) for k in ("width", "height", "anchor")]
    if (
        not all(math.isfinite(v) for v in values)
        or min(values[:2]) <= 0
        or not 0 <= values[2] <= values[0]
    ):
        raise ValueError(
            "Atlas blocks require finite, positive dimensions and an in-bounds anchor."
        )
    return BlockExtent(values[0], values[1], values[2], row.attrib["data-atlas-phase"])


def _text_panel(
    element: ET.Element, width: float, annotation_size: float, *, label: str = ""
) -> ScenePanel:
    """Keep each material input unique while wrapping its exact printed sequence."""
    root = ET.Element(f"{{{SVG}}}g", element.attrib)
    for key in ("transform", "x", "y", "text-anchor", "font-size", "font-family"):
        root.attrib.pop(key, None)
    y = annotation_size
    if label:
        ET.SubElement(
            root, f"{{{SVG}}}text", x="12", y=str(y), attrib={"font-size": str(annotation_size)}
        ).text = label
        y += annotation_size + 6
    texts = [e for e in element.iter() if e.tag.endswith("}text")]
    for text in texts:
        sequence = text.get("font-family") == "monospace"
        size = 16 if sequence else annotation_size
        lines = wrap(
            "".join(text.itertext()),
            width=max(1, int((width - 24) / (size * 0.64))),
            replace_whitespace=False,
            drop_whitespace=False,
        )
        group = ET.SubElement(root, f"{{{SVG}}}g")
        for line in lines:
            ET.SubElement(
                group,
                f"{{{SVG}}}text",
                x="12",
                y=str(y),
                attrib={
                    "font-size": str(size),
                    "font-family": "monospace" if sequence else "Arial, Helvetica, sans-serif",
                },
            ).text = line
            y += size + 6
    return ScenePanel(root, y + 6, {})


def paginate_blocks(root: ET.Element, scale: float) -> tuple[tuple[bytes, ...], dict[str, Any]]:
    content = next(e for e in root if e.tag.rsplit("}", 1)[-1] == "g")
    rows = [e for e in content if "data-atlas-state" in e.attrib]
    if not rows or [int(e.attrib["data-atlas-order"]) for e in rows] != list(range(len(rows))):
        raise ValueError("Atlas block order must be unique and chronological.")
    ids = [e.attrib["data-atlas-state"] for e in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Atlas block identities must be unique.")
    place_route(tuple(_extent(row) for row in rows))
    # Preserve native base size; prose uses the continuation page's type budget.
    scale = max(scale, PUBLICATION.sequence_pt / 16, PROSE_SIZE_PT / ANNOTATION_SIZE)
    width = PUBLICATION.width_pt / scale
    body_width = width - 2 * MARGIN
    annotation_size = PROSE_SIZE_PT / scale
    blocks: list[ScenePanel] = []
    for row in rows:
        blocks.extend(scene_panels(row, body_width))
        operation = next((e for e in row.iter() if e.get("data-operation")), None)
        inputs = [e for e in row.iter() if e.get("data-atlas-input")]
        if operation is not None:
            blocks.append(
                _text_panel(operation, body_width, annotation_size, label="Next operation")
            )
        blocks.extend(_text_panel(e, body_width, annotation_size) for e in inputs)
    for key in (e for e in content if e.get("data-site-key")):
        entries = [
            (str(name), str(color))
            for name, color in json.loads(key.attrib["data-site-key-entries"])
        ]
        drawing, height = draw_site_key(entries, body_width, 0, size=annotation_size)
        blocks.append(
            ScenePanel(ET.fromstring(drawing.replace("<g ", f'<g xmlns="{SVG}" ', 1)), height, {})
        )
    blocks.extend(
        _text_panel(e, body_width, annotation_size) for e in content if e.get("data-atlas-notes")
    )
    return paginate_panels(blocks, width, scale)


def paginate_panels(
    blocks: list[ScenePanel],
    width: float,
    scale: float,
    *,
    title: str = "Molecular route",
    schema: str = "hop.molecular-atlas-print/v1",
    shared_definitions: ET.Element | None = None,
) -> tuple[tuple[bytes, ...], dict[str, Any]]:
    """Pack addressed molecular panels using one physical type and page contract."""
    limit = PUBLICATION.height_pt / scale - 86
    groups: list[list[ScenePanel]] = []
    heights: list[float] = []
    for block in blocks:
        if block.height > limit:
            raise ValueError(
                "A scene panel exceeds the print height; split its vertical content explicitly."
            )
        if not groups or heights[-1] + block.height + 18 > limit:
            groups.append([])
            heights.append(0)
        if groups[-1]:
            heights[-1] += 18
        groups[-1].append(block)
        heights[-1] += block.height
    pages: list[bytes] = []
    descriptions: list[dict[str, Any]] = []
    for ordinal, (group, body_height) in enumerate(zip(groups, heights, strict=True), 1):
        height = body_height + 86
        page = ET.Element(
            f"{{{SVG}}}svg",
            {
                "viewBox": f"0 0 {width} {height}",
                "width": f"{PUBLICATION.width_pt}pt",
                "height": f"{height * scale:.8f}pt",
                "data-atlas-page": str(ordinal),
                "font-family": "Arial, Helvetica, sans-serif",
                "fill": "#243740",
            },
        )
        definitions = ET.SubElement(page, f"{{{SVG}}}defs")
        if shared_definitions is not None:
            definitions.extend(deepcopy(list(shared_definitions)))
        ET.SubElement(page, f"{{{SVG}}}rect", width="100%", height="100%", fill="white")
        ET.SubElement(
            page, f"{{{SVG}}}text", x=str(MARGIN), y="24", attrib={"font-size": "22"}
        ).text = f"{title} · {ordinal}/{len(groups)}"
        y = 44.0
        descriptions.append(
            {
                "page": ordinal,
                "state_ids": [],
                "panels": [],
                "width_pt": PUBLICATION.width_pt,
                "height_pt": height * scale,
            }
        )
        for block in group:
            placed = ET.SubElement(page, f"{{{SVG}}}g", transform=f"translate({MARGIN} {y})")
            panel = deepcopy(block.element)
            for parent in panel.iter():
                for child in list(parent):
                    if child.tag == f"{{{SVG}}}defs":
                        definitions.extend(child)
                        parent.remove(child)
            placed.append(panel)
            for element in placed.iter():
                if element.get("data-stage-title"):
                    element.set("font-size", str(PUBLICATION.stage_title_pt / scale))
            if block.description:
                descriptions[-1]["panels"].append(block.description)
                if block.description["state_id"] not in descriptions[-1]["state_ids"]:
                    descriptions[-1]["state_ids"].append(block.description["state_id"])
            y += block.height + 18
        ET.SubElement(
            page, f"{{{SVG}}}text", x=str(MARGIN), y=str(height - 14), attrib={"font-size": "18"}
        ).text = "Print at 100%: bases ≥ 8 pt. View splits do not represent molecular cuts."
        pages.append(ET.tostring(page, encoding="utf-8"))
    return tuple(pages), {
        "schema": schema,
        "minimum_sequence_font_pt": PUBLICATION.sequence_pt,
        "minimum_annotation_font_pt": PUBLICATION.annotation_pt,
        "page_width_pt": PUBLICATION.width_pt,
        "scale_pt_per_unit": scale,
        "pages": descriptions,
    }
