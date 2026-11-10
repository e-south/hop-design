"""A literal, lossless single-row reading of the captured mixed comparison features."""

import json
from math import isfinite
from textwrap import wrap
from typing import Any, cast
from xml.etree import ElementTree as ET

from ..molecular.primitives.typography import text_width


def render_comparison_vector(packet: dict[str, Any], *, width_pt: float = 504) -> bytes:
    """Keep values in recorded order; a wide record grows rather than losing tokens."""
    if isinstance(width_pt, bool) or not isfinite(width_pt) or not 180 <= width_pt <= 720:
        raise ValueError("Feature row width must be 180 to 720 points.")
    fields = packet["vector"]
    label_size, value_size, contact_size = 7.2, 9.0, 8.5
    widths, headers = [], []
    for feature in fields:
        value = feature["value"]
        word = (
            "".join(value)
            if isinstance(value, list | tuple) and feature.get("encoding") != "contacts"
            else str(value)
        )
        ink = (
            len(value) * 5.1
            if feature.get("encoding") == "contacts"
            else text_width(word, value_size)
        )
        label = feature["label"]
        width = (
            max(
                [
                    ink,
                    text_width(feature.get("unit", ""), label_size),
                    *[text_width(w, label_size) for w in label.split()],
                ]
            )
            + 4
        )
        widths.append(width)
        lines = wrap(
            label,
            width=max(4, int((width - 4) / 3.8)),
            break_long_words=False,
            break_on_hyphens=False,
        )
        headers.append([*lines, *([feature["unit"]] if feature.get("unit") else [])])
    width = max(width_pt, 41 + sum(widths) + 3 * max(0, len(fields) - 1))
    body_y = max((len(lines) for lines in headers), default=1) * 8.5 + 17
    height = body_y + 25
    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": f"{width:g}pt",
            "height": f"{height:g}pt",
            "viewBox": f"0 0 {width:g} {height:g}",
            "data-preparation-id": packet["identity"],
            "data-comparison-display": "literal-row",
            "role": "img",
        },
    )
    ET.SubElement(svg, "title").text = (
        "X: captured mixed-type molecular features in recorded order. Geometry retains its units; "
        "contacts retain strand order and pairing class. Exact encodings and comparison policy "
        "remain unchanged."
    )
    ET.SubElement(svg, "metadata").text = json.dumps(
        packet, ensure_ascii=False, separators=(",", ":")
    )
    ET.SubElement(svg, "rect", {"width": str(width), "height": str(height), "fill": "white"})

    def text(
        parent: ET.Element,
        x: float,
        y: float,
        value: str,
        size: float,
        *,
        mono: bool = False,
        **attrs: str,
    ) -> None:
        node = ET.SubElement(
            parent,
            "text",
            {
                "x": str(x),
                "y": str(y),
                "font-size": str(size),
                "font-family": "Courier New,monospace" if mono else "Arial,sans-serif",
                "fill": "#253b40",
                "text-anchor": "middle",
                **attrs,
            },
        )
        node.text = value

    text(svg, 11, body_y + 10, "X =", 12)
    for side, x, sign in (("open", 29, 1), ("close", width - 4, -1)):
        ET.SubElement(
            svg,
            "path",
            {
                "data-vector-bracket": side,
                "d": f"M{x + sign * 4},{body_y - 10} H{x} V{body_y + 20} H{x + sign * 4}",
                "fill": "none",
                "stroke": "#253b40",
                "stroke-width": ".8",
            },
        )
    x = 35.0
    gap = (width - 41 - sum(widths)) / max(1, len(fields) - 1)
    for index, (feature, cell_width, lines) in enumerate(zip(fields, widths, headers, strict=True)):
        item = ET.SubElement(
            svg,
            "g",
            {
                "data-feature": feature["key"],
                "data-feature-row": "0",
                "data-vector-index": str(index),
                "data-encoded": json.dumps(
                    feature["encoded"], ensure_ascii=False, separators=(",", ":")
                ),
            },
        )
        ET.SubElement(item, "title").text = json.dumps(feature, ensure_ascii=False)
        center = x + cell_width / 2
        for line_no, line in enumerate(lines):
            text(item, center, 9 + line_no * 8.5, line, label_size)
        if feature.get("encoding") == "contacts":
            contacts = feature["value"]
            left = center - max(0, len(contacts) - 1) * 5.1 / 2
            for j, (upper, lower, kind) in enumerate(contacts):
                cx = left + j * 5.1
                pair = ET.SubElement(
                    item, "g", {"data-contact-class": kind, "data-contact-index": str(j)}
                )
                text(pair, cx, body_y, upper, contact_size, mono=True)
                text(pair, cx, body_y + 18, lower, contact_size, mono=True)
                ET.SubElement(
                    pair,
                    "path",
                    {
                        "d": f"M{cx},{body_y + 2} V{body_y + 10}"
                        if kind == "watson_crick"
                        else f"M{cx},{body_y + 2} l2,4 l-2,4 l-2,-4 Z",
                        "stroke": "#70838A" if kind == "watson_crick" else "#a35b32",
                        "stroke-width": ".65",
                        "fill": "none",
                        "data-contact-glyph": "line" if kind == "watson_crick" else "diamond",
                    },
                )
        else:
            value = feature["value"]
            word = "".join(value) if isinstance(value, list | tuple) else str(value)
            text(item, center, body_y + 9, word, value_size, mono=True)
        x += cell_width + gap
    return cast(bytes, ET.tostring(svg, encoding="utf-8", xml_declaration=True))
