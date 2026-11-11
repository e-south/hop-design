"""A compact numeric display of the saved comparison with exact lookup metadata."""

import json
from math import isfinite
from typing import Any, cast
from xml.etree import ElementTree as ET

from ..molecular.primitives.typography import text_width


def render_comparison_vector(packet: dict[str, Any], *, width_pt: float = 504) -> bytes:
    """Measurements retain units; other numbers identify field-specific dictionary entries."""
    if isinstance(width_pt, bool) or not isfinite(width_pt) or not 180 <= width_pt <= 720:
        raise ValueError("Feature row width must be 180 to 720 points.")
    fields = packet["vector"]
    if fields and (
        "presentation" not in packet or any("display_value" not in field for field in fields)
    ):
        raise ValueError(
            "Numeric comparison display requires a current projection with field codes."
        )
    font, value_font = 7.2, 9.0
    start, end = 26.0, width_pt - 7
    pitch = (end - start) / max(1, len(fields))
    short_units = {"positions": "pos", "contacts": "ct"}
    labels = [
        f["label"] + (f" ({short_units.get(f['unit'], f['unit'])})" if f.get("unit") else "")
        for f in fields
    ]
    height = 50 + max((text_width(label, font) * 0.707 for label in labels), default=0)
    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": f"{width_pt:g}pt",
            "height": f"{height:g}pt",
            "viewBox": f"0 0 {width_pt:g} {height:g}",
            "data-preparation-id": packet["identity"],
            "data-comparison-display": "numeric-row",
            "role": "img",
        },
    )
    ET.SubElement(svg, "title").text = (
        "X: measurements and nominal field codes from the saved comparison. "
        "Codes identify exact values in their field dictionaries; "
        "their numerical separation is not a distance."
    )
    ET.SubElement(svg, "metadata").text = json.dumps(
        packet, ensure_ascii=False, separators=(",", ":")
    )

    def text(parent, x, y, value, size=font, **attrs):
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

    groups = packet.get("presentation", {}).get("groups", {})
    for block, style in groups.items():
        indices = [i for i, field in enumerate(fields) if field["key"].split(".")[0] == block]
        if not indices:
            continue
        left, right = start + indices[0] * pitch, start + (indices[-1] + 1) * pitch
        group = ET.SubElement(svg, "g", {"data-feature-group": block})
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
                "d": f"M{left + inset},12 H{right - inset} L{right},23 H{left} Z",
                "fill": style["fill"],
                "fill-opacity": ".35",
            },
        )
        text(group, (left + right) / 2, 9, style["label"])
    text(svg, 10, 33, "X =", 10)
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
                "data-vector-index": str(i),
                "data-encoded": json.dumps(
                    field["encoded"], ensure_ascii=False, separators=(",", ":")
                ),
            },
        )
        ET.SubElement(group, "title").text = json.dumps(field, ensure_ascii=False)
        text(
            group, x, 33, field["display_value"], value_font, **{"data-display-value": field["key"]}
        )
        text(
            group,
            x,
            45,
            label,
            **{
                "text-anchor": "end",
                "transform": f"rotate(-45 {x} 45)",
                "data-feature-label": field["key"],
            },
        )
    return cast(bytes, ET.tostring(svg, encoding="utf-8", xml_declaration=True))
