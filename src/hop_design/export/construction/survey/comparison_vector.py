"""Exact typed comparison values for a selected publication point."""

import json
from typing import Any, cast
from xml.etree import ElementTree as ET


def render_comparison_vector(packet: dict[str, Any]) -> bytes:
    """Draw complete values on one row; never wrap or truncate a coordinate.

    The natural SVG width follows its content. Figure composition owns its final
    placement and must check print size rather than silently shrink its type.
    Constants and the full distance policy remain in the embedded JSON record.
    """
    fields = packet["vector"]
    encoded = [json.dumps(f["encoded"], ensure_ascii=False, separators=(",", ":")) for f in fields]
    labels = [f["label"] + (f" · {f['unit']}" if f.get("unit") else "") for f in fields]
    widths = [
        max(48, len(code) * 5.2 + 12, len(label) * 4.8 + 12)
        for label, code in zip(labels, encoded, strict=True)
    ]
    width, height = sum(widths) + 42, 75
    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {width} {height}",
            "width": f"{width}pt",
            "height": f"{height}pt",
            "data-preparation-id": packet["identity"],
            "role": "img",
        },
    )
    ET.SubElement(svg, "title").text = (
        "Selected molecular comparison descriptor. Contact codes are nominal labels; "
        "the recorded comparison policy defines dissimilarity, not Euclidean distance on codes."
    )
    ET.SubElement(svg, "metadata").text = json.dumps(
        packet, ensure_ascii=False, separators=(",", ":")
    )

    def text(
        parent: ET.Element,
        x: float,
        y: float,
        value: str,
        *,
        mono: bool = False,
        anchor: str = "middle",
        **attributes: str,
    ) -> None:
        ET.SubElement(
            parent,
            "text",
            {
                "x": str(x),
                "y": str(y),
                "font-family": "Courier New,monospace" if mono else "Arial,sans-serif",
                "font-size": "8.5",
                "fill": "#253b40",
                "text-anchor": anchor,
                **attributes,
            },
        ).text = value

    text(svg, 2, 62, "x = [", anchor="start")
    x = 31.0
    for feature, label, code, cell in zip(fields, labels, encoded, widths, strict=True):
        group = ET.SubElement(svg, "g", {"data-feature": feature["key"]})
        center = x + cell / 2
        text(group, center, 12, label)
        if feature.get("encoding") == "contacts":
            text(group, center, 27, "".join(c[0] for c in feature["value"]), mono=True)
            text(group, center, 38, "".join(c[1] for c in feature["value"]), mono=True)
        elif feature["key"].startswith("sequences."):
            text(group, center, 32, "".join(feature["value"]), mono=True)
        ET.SubElement(
            group,
            "path",
            {
                "d": f"M{x + 4} 47 H{x + cell - 4}",
                "stroke": "#819b9c",
                "stroke-width": "0.5",
            },
        )
        text(group, center, 62, code, mono=True, **{"data-encoded": code})
        x += cell
        if feature is not fields[-1]:
            text(svg, x, 62, ",")
    text(svg, width - 3, 62, "]", anchor="end")
    return cast(bytes, ET.tostring(svg, encoding="utf-8", xml_declaration=True))
