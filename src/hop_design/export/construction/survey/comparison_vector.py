"""
--------------------------------------------------------------------------------
HOP Design
hop-design/src/hop_design/export/construction/survey/comparison_vector.py

Render schematic comparison fields with exact values retained in lookup metadata.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from math import cos, isfinite, radians, sin
from typing import Any, cast
from xml.etree import ElementTree as ET

from ..molecular.primitives.typography import text_width


def render_comparison_vector(packet: dict[str, Any], *, width_pt: float | None = None) -> bytes:
    """Measurements retain units; other numbers identify field-specific dictionary entries."""
    presentation = packet.get("presentation", {})
    schematic = presentation.get("display") == "schematic-glyphs"
    fields = packet["vector"]
    source_indices = {field["key"]: i for i, field in enumerate(fields)}
    if schematic:
        by_key = {field["key"]: field for field in fields}
        order = presentation["display_order"]
        if len(by_key) != len(fields) or len(order) != len(fields) or set(order) != set(by_key):
            raise ValueError("Comparison display order must preserve every vector field.")
        fields = [by_key[key] for key in order]
    if fields and (
        "presentation" not in packet or any("display_value" not in field for field in fields)
    ):
        raise ValueError(
            "Numeric comparison display requires a current projection with field codes."
        )
    font, value_font = 7.2, 9.0
    angle, pitch = -45.0, 13.2
    if schematic:
        font, pitch, angle = (
            float(presentation[key]) for key in ("font_size", "field_pitch", "label_angle")
        )
        if not all(isfinite(value) for value in (font, pitch, angle)) or (
            font <= 0 or pitch <= 0 or not -90 <= angle <= 0
        ):
            raise ValueError(
                "Comparison typography requires positive sizes and a descending label angle."
            )
    horizontal, vertical = cos(radians(angle)), abs(sin(radians(angle)))
    short_units = {"positions": "pos", "contacts": "ct"}
    labels = [
        f["label"]
        + (f" ({short_units.get(f['unit'], f['unit'])})" if f.get("unit") and not schematic else "")
        for f in fields
    ]
    margin = (
        max(
            26,
            max(
                (
                    text_width(label, font) * horizontal + font * vertical - (i + 0.5) * pitch + 2
                    for i, label in enumerate(labels)
                ),
                default=0,
            ),
        )
        if schematic
        else 26
    )
    width_pt = (
        max(180, margin + pitch * len(fields) + 7)
        if width_pt is None and schematic
        else (504 if width_pt is None else width_pt)
    )
    if isinstance(width_pt, bool) or not isfinite(width_pt) or not 180 <= width_pt <= 720:
        raise ValueError("Feature row width must be 180 to 720 points.")
    start, end = margin, width_pt - 7
    pitch = pitch if schematic else (end - start) / max(1, len(fields))
    if schematic:
        if len(fields) * pitch > end - start + 1e-9:
            raise ValueError("Comparison glyphs require a wider figure.")
        start += ((end - start) - len(fields) * pitch) / 2
        end = start + len(fields) * pitch
    height = 50 + max(
        (text_width(label, font) * (vertical if schematic else 0.707) for label in labels),
        default=0,
    )
    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": f"{width_pt:g}pt",
            "height": f"{height:g}pt",
            "viewBox": f"0 0 {width_pt:g} {height:g}",
            "data-preparation-id": packet["identity"],
            "data-comparison-display": "schematic-glyphs" if schematic else "numeric-row",
            "role": "img",
        },
    )
    ET.SubElement(svg, "title").text = (
        "X: field-type schematics from the saved comparison. Glyphs identify inputs, "
        "not their values; exact measurements and nominal codes remain in each field's metadata."
        if schematic
        else "X: measurements and nominal field codes from the saved comparison. "
        "Codes identify exact values in their field dictionaries; "
        "their numerical separation is not a distance."
    )
    ET.SubElement(svg, "metadata").text = json.dumps(
        packet, ensure_ascii=False, separators=(",", ":")
    )

    def text(
        parent: ET.Element,
        x: float,
        y: float,
        value: object,
        size: float = font,
        **attrs: str,
    ) -> ET.Element:
        node = ET.SubElement(
            parent,
            "text",
            {
                "x": str(x),
                "y": str(y),
                "font-size": str(size),
                "font-family": "Arial,sans-serif",
                "fill": "#253b40",
                "text-anchor": "middle",
                "font-weight": "normal",
                **attrs,
            },
        )
        node.text = str(value)
        return node

    groups = (
        {group["key"]: group for group in presentation["schema_groups"]}
        if schematic
        else presentation.get("groups", {})
    )
    for block, style in groups.items():
        indices = [
            i
            for i, field in enumerate(fields)
            if (
                field["key"] in style["fields"]
                if schematic
                else field["key"].split(".")[0] == block
            )
        ]
        if not indices:
            continue
        left, right = start + indices[0] * pitch, start + (indices[-1] + 1) * pitch
        group = ET.SubElement(svg, "g", {"data-feature-group": block})
        ET.SubElement(group, "title").text = style["label"]
        ET.SubElement(
            group,
            "rect",
            {
                "x": str(left + 1),
                "y": "1",
                "width": str(right - left - 2),
                "height": "11",
                "rx": "1.2",
                "fill": style["fill"],
            },
        )
        inset = min(5, (right - left) * 0.08)
        ET.SubElement(
            group,
            "path",
            {
                "d": f"M{left + inset},12 H{right - inset} L{right},21 H{left} Z",
                "fill": style["fill"],
                "fill-opacity": ".25",
            },
        )
        ET.SubElement(
            group,
            "line",
            {
                "x1": str(left),
                "x2": str(right),
                "y1": "22",
                "y2": "22",
                "stroke": "#8a9699",
                "stroke-width": ".5",
                "data-feature-span": block,
            },
        )
        if not schematic or text_width(style["label"], font) <= right - left - 2:
            text(group, (left + right) / 2, 9, style["label"])
    text(svg, 10, 33, "X =", font if schematic else 10)
    for side, x, sign in (("open", start - 3, 1), ("close", end + 2, -1)):
        ET.SubElement(
            svg,
            "path",
            {
                "d": f"M{x + sign * 3},24 H{x} V36 H{x + sign * 3}",
                "stroke": "#253b40",
                "data-vector-bracket": side,
                "stroke-width": ".7",
                "fill": "none",
            },
        )
    for i, (field, label) in enumerate(zip(fields, labels, strict=True)):
        x = start + (i + 0.5) * pitch
        group = ET.SubElement(
            svg,
            "g",
            {
                "data-feature": field["key"],
                "data-feature-row": "0",
                "data-vector-index": str(source_indices[field["key"]]),
                **({"data-display-x": str(x)} if schematic else {}),
                **(
                    {
                        "tabindex": "0",
                        "role": "img",
                        "aria-label": json.dumps(field, ensure_ascii=False),
                    }
                    if schematic
                    else {}
                ),
                "data-encoded": json.dumps(
                    field["encoded"], ensure_ascii=False, separators=(",", ":")
                ),
            },
        )
        ET.SubElement(group, "title").text = json.dumps(field, ensure_ascii=False)
        if schematic:
            glyph = presentation["glyphs"][field["key"]]
            holder = ET.SubElement(
                group,
                "g",
                {
                    "data-input-glyph": field["key"],
                    "transform": f"translate({x} 31)",
                    "aria-hidden": "true",
                },
            )
            _append_glyph(holder, glyph["nodes"])
        else:
            text(
                group,
                x,
                33,
                field["display_value"],
                value_font,
                **{"data-display-value": field["key"]},
            )
        text(
            group,
            x,
            45,
            label,
            **{
                "text-anchor": "end",
                "transform": f"rotate({angle:g} {x} 45)",
                "data-feature-label": field["key"],
            },
        )
    return cast(bytes, ET.tostring(svg, encoding="utf-8", xml_declaration=True))


def _append_glyph(parent: ET.Element, nodes: list[dict[str, Any]]) -> None:
    """Only inert geometry can enter the shared browser/static glyph vocabulary."""
    allowed = {
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "cx",
        "cy",
        "r",
        "width",
        "height",
        "rx",
        "d",
        "fill",
        "stroke",
        "stroke-width",
        "stroke-opacity",
        "fill-opacity",
        "stroke-linecap",
        "stroke-linejoin",
        "data-fixed-stem",
        "data-measured-flank",
        "data-end-context",
    }
    for node in nodes:
        if (
            node["tag"] not in {"g", "line", "path", "rect", "circle"}
            or set(node["attrs"]) - allowed
        ):
            raise ValueError("Comparison glyphs require inert SVG geometry.")
        if any("url(" in value.lower() for value in node["attrs"].values()):
            raise ValueError("Comparison glyphs cannot reference external paint.")
        element = ET.SubElement(parent, node["tag"], node["attrs"])
        _append_glyph(element, node.get("children", []))
