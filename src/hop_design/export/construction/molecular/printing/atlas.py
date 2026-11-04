"""Paginate the exact atlas at a readable physical scale, without redrawing bases."""

import math
from copy import deepcopy
from itertools import pairwise
from typing import Any
from xml.etree import ElementTree as ET

from .blocks import paginate_blocks

SVG = "http://www.w3.org/2000/svg"
MINIMUM_SEQUENCE_PT = 8.0
PAGE_HEIGHT_PT = 792.0
HEADER = 42.0
FOOTER = 36.0


def _sequence_font(root: ET.Element) -> float:
    fonts: list[float] = []
    for element in root.iter():
        if "data-base-index" in element.attrib or element.get("font-family") == "monospace":
            fonts.extend(
                float(text.attrib["font-size"])
                for text in element.iter()
                if text.tag.rsplit("}", 1)[-1] == "text" and "font-size" in text.attrib
            )
    if not fonts or any(not math.isfinite(font) or font <= 0 for font in fonts):
        raise ValueError("Atlas print requires explicitly sized nucleotide text.")
    return min(fonts)


def paginate_atlas(svg: bytes) -> tuple[tuple[bytes, ...], dict[str, Any]]:
    """Print native scenes without shrinking bases below the physical type budget.

    Current block atlases use fixed-width pages and explicit coordinate panels.
    Original addresses remain unique across those view continuations. Legacy
    single-column SVGs retain their original whole-state pagination behavior.
    """
    root = ET.fromstring(svg)
    if root.get("data-atlas") != "true":
        raise ValueError("Print pagination requires a generated molecular atlas.")
    x, y, width, height = map(float, root.attrib["viewBox"].split())
    if x or y or not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise ValueError("Atlas print requires positive dimensions and a zero origin.")
    if root.get("data-atlas-layout") == "columns-with-finish":
        return paginate_blocks(root, MINIMUM_SEQUENCE_PT / _sequence_font(root))
    content = next(e for e in root if e.tag.rsplit("}", 1)[-1] == "g")
    children = list(content)
    rows = [(i, e) for i, e in enumerate(children) if "data-atlas-state" in e.attrib]
    starts = [float(e.attrib["data-atlas-y"]) for _, e in rows]
    if not starts or starts[0] < 0 or starts[-1] >= height:
        raise ValueError("Atlas print requires in-bounds recorded states.")
    if any(a >= b for a, b in pairwise(starts)):
        raise ValueError("Atlas states must retain their chronological layout order.")
    scale = MINIMUM_SEQUENCE_PT / _sequence_font(root)
    limit = PAGE_HEIGHT_PT / scale - HEADER - FOOTER
    # First block retains the route title and comparison introduction. Later blocks
    # begin at a state boundary, keeping the preceding operation on its source page.
    blocks = []
    for index, (offset, state) in enumerate(rows):
        start = 0.0 if index == 0 else starts[index]
        end = starts[index + 1] if index + 1 < len(rows) else height
        stop = rows[index + 1][0] if index + 1 < len(rows) else len(children)
        blocks.append(
            (
                start,
                end,
                state.attrib["data-atlas-state"],
                children[0 if index == 0 else offset : stop],
            )
        )
    groups: list[list[Any]] = []
    for block in blocks:
        if not groups or block[1] - groups[-1][0][0] > limit:
            groups.append([])
        groups[-1].append(block)
    pages, descriptions = [], []
    for ordinal, group in enumerate(groups, 1):
        start, end = group[0][0], group[-1][1]
        page_height = HEADER + end - start + FOOTER
        page = ET.Element(
            f"{{{SVG}}}svg",
            {
                "viewBox": f"0 0 {width} {page_height}",
                "width": f"{width * scale:.8f}pt",
                "height": f"{page_height * scale:.8f}pt",
                "data-atlas-page": str(ordinal),
            },
        )
        ET.SubElement(page, f"{{{SVG}}}rect", width="100%", height="100%", fill="white")
        label = ET.SubElement(
            page,
            f"{{{SVG}}}text",
            x="28",
            y="26",
            attrib={
                "font-size": "16",
                "font-family": "Arial, Helvetica, sans-serif",
                "fill": "#243740",
            },
        )
        label.text = f"Molecular route · {ordinal}/{len(groups)}"
        placed = ET.SubElement(
            page, f"{{{SVG}}}g", {**content.attrib, "transform": f"translate(0 {HEADER - start})"}
        )
        for _, _, _, elements in group:
            placed.extend(deepcopy(elements))
        footer = ET.SubElement(
            page,
            f"{{{SVG}}}text",
            x="28",
            y=str(page_height - 12),
            attrib={
                "font-size": "14",
                "font-family": "Arial, Helvetica, sans-serif",
                "fill": "#52656D",
            },
        )
        footer.text = "Print at native size: nucleotide text ≥ 8 pt." + (
            f" Continue on page {ordinal + 1}."
            if ordinal < len(groups)
            else " End of recorded route."
        )
        pages.append(ET.tostring(page, encoding="utf-8"))
        descriptions.append(
            {
                "page": ordinal,
                "state_ids": [b[2] for b in group],
                "width_pt": width * scale,
                "height_pt": page_height * scale,
            }
        )
    return tuple(pages), {
        "schema": "hop.molecular-atlas-print/v1",
        "minimum_sequence_font_pt": MINIMUM_SEQUENCE_PT,
        "scale_pt_per_unit": scale,
        "pages": descriptions,
    }


def native_route_plate(svg: bytes) -> tuple[bytes, dict[str, Any]]:
    """Give a generated route physical dimensions without moving or dropping its content.

    The existing source viewBox and molecular layout remain unchanged. Fixed-width
    continuation pages are separate reading outputs, not replacements for this plate.
    Reference-width measurements report the consequence of shrinking this same view;
    they are geometric measurements rather than a journal-specific acceptance rule.
    """
    root = ET.fromstring(svg)
    if root.get("data-atlas") != "true":
        raise ValueError("Native plate export requires a generated molecular atlas.")
    source_viewbox = root.attrib["viewBox"]
    x, y, width, height = map(float, source_viewbox.split())
    if x or y or not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise ValueError("Native plate export requires positive dimensions and a zero origin.")
    sequence_font = _sequence_font(root)
    if not math.isfinite(sequence_font):
        raise ValueError("Native plate export requires finite nucleotide text size.")
    scale = MINIMUM_SEQUENCE_PT / sequence_font
    # This is the existing working print width, not a new manuscript policy.
    from ...presentation.print_contract import PUBLICATION

    reference_width = PUBLICATION.width_pt
    reference_sequence = sequence_font * reference_width / width
    root.set("width", f"{width * scale:.8f}pt")
    root.set("height", f"{height * scale:.8f}pt")
    return ET.tostring(root, encoding="utf-8"), {
        "schema": "hop.molecular-atlas-plate/v1",
        "layout": root.get("data-atlas-layout", "legacy"),
        "source_viewbox": source_viewbox,
        "preserves_source_viewbox": True,
        "minimum_sequence_font_pt": MINIMUM_SEQUENCE_PT,
        "source_sequence_font_units": sequence_font,
        "scale_pt_per_unit": scale,
        "width_pt": width * scale,
        "height_pt": height * scale,
        "reference_width_pt": reference_width,
        "reference_sequence_font_pt": reference_sequence,
        "reference_width_meets_sequence_minimum": reference_sequence >= MINIMUM_SEQUENCE_PT,
        "reference_sequence_deficit_pt": max(0.0, MINIMUM_SEQUENCE_PT - reference_sequence),
    }
