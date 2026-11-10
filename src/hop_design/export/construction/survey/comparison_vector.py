"""Readable decoded comparison values, retaining the exact encoded vector."""

import json
from textwrap import wrap
from typing import Any, cast
from xml.etree import ElementTree as ET

from reportlab.pdfbase.pdfmetrics import stringWidth  # type: ignore[import-untyped]

from ..molecular.primitives.typography import text_width


def render_comparison_vector(packet: dict[str, Any]) -> bytes:
    """Fit whole decoded features at eight-and-a-half point type, in vector order.

    Nominal contact IDs are redundant with the decoded contacts. Their complete
    encoding and the comparison policy remain in metadata and feature attributes.
    """
    fields = packet["vector"]
    font, width, gap = 8.5, 504, 6
    labels = [f["label"] + (f" ({f['unit']})" if f.get("unit") else "") for f in fields]

    def rows(feature: dict[str, Any]) -> list[str]:
        if feature.get("encoding") == "contacts":
            return ["".join(c[i] for c in feature["value"]) or "∅" for i in (0, 1)]
        value = feature["value"]
        return ["".join(value) if isinstance(value, list | tuple) else str(value)]

    decoded = [rows(f) for f in fields]
    sizes = [
        max(
            26,
            max(text_width(word, font) for word in label.split()) + 4,
            max(float(stringWidth(line, "Courier", font)) for line in values) + 8,
        )
        for label, values in zip(labels, decoded, strict=True)
    ]
    bands: list[list[int]] = [[]] if fields else []
    for i, size in enumerate(sizes):
        if bands[-1] and sum(sizes[j] + gap for j in bands[-1]) + size > width - 42:
            bands.append([])
        bands[-1].append(i)
    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": "7in",
            "data-preparation-id": packet["identity"],
            "data-comparison-display": "decoded",
            "role": "img",
        },
    )
    ET.SubElement(svg, "title").text = (
        "Decoded molecular comparison descriptor, in the recorded vector order. "
        "Contact rows retain ordered bases and contact classes. Exact nominal encodings "
        "and the comparison policy remain in metadata; codes are not numerical distances."
    )
    ET.SubElement(svg, "metadata").text = json.dumps(
        packet, ensure_ascii=False, separators=(",", ":")
    )
    background = ET.SubElement(svg, "rect", {"width": str(width), "fill": "white"})

    def text(
        parent: ET.Element,
        x: float,
        y: float,
        value: str,
        *,
        mono: bool = False,
        anchor: str = "middle",
        **attrs: str,
    ) -> ET.Element:
        node = ET.SubElement(
            parent,
            "text",
            {
                "x": str(x),
                "y": str(y),
                "font-size": str(font),
                "fill": "#253b40",
                "font-family": "Courier New,monospace" if mono else "Arial,sans-serif",
                "text-anchor": anchor,
                **attrs,
            },
        )
        node.text = value
        return node

    y = 10.0
    if not fields:
        text(svg, 2, 18, "x = []", anchor="start")
        y = 36.0
    for band_no, band in enumerate(bands):
        headings = {
            i: wrap(labels[i], width=max(4, int((sizes[i] - 2) / 4.8)), break_long_words=False)
            for i in band
        }
        value_y = y + max(len(v) for v in headings.values()) * 10 + 12
        text(svg, 2, value_y + 6, "x = [" if band_no == 0 else "[cont.]", anchor="start")
        x = 31.0
        for i in band:
            feature, cell = fields[i], sizes[i]
            center = x + cell / 2
            group = ET.SubElement(
                svg,
                "g",
                {
                    "data-feature": feature["key"],
                    "data-encoded": json.dumps(
                        feature["encoded"], ensure_ascii=False, separators=(",", ":")
                    ),
                    "data-vector-index": str(i),
                    "data-display-band": str(band_no),
                },
            )
            ET.SubElement(group, "title").text = json.dumps(feature, ensure_ascii=False)
            for n, line in enumerate(headings[i]):
                text(group, center, y + n * 10, line)
            if feature.get("encoding") == "contacts":
                contacts = feature["value"]
                start = center - (len(contacts) - 1) * 5.1 / 2
                for j, (upper, lower, kind) in enumerate(contacts):
                    cx = start + j * 5.1
                    pair = ET.SubElement(group, "g", {"data-contact-class": kind})
                    text(pair, cx, value_y, upper, mono=True, **{"data-contact-row": "source"})
                    text(pair, cx, value_y + 18, lower, mono=True, **{"data-contact-row": "paired"})
                    path = f"M{cx},{value_y + 2} V{value_y + 10}"
                    if kind != "watson_crick":
                        path = f"M{cx},{value_y + 2} l2,4 l-2,4 l-2,-4 Z"
                    ET.SubElement(
                        pair,
                        "path",
                        {
                            "d": path,
                            "stroke": "#70838A",
                            "stroke-width": ".65",
                            "fill": "none",
                            "data-contact-glyph": "line" if kind == "watson_crick" else "diamond",
                        },
                    )
            else:
                text(group, center, value_y + 6, decoded[i][0], mono=True)
            x += cell + gap
            if i != len(fields) - 1:
                text(svg, x - gap / 2, value_y + 6, ",")
        if band_no == len(bands) - 1:
            text(svg, min(width - 3, x), value_y + 6, "]", anchor="end")
        y = value_y + 38
    text(
        svg,
        4,
        y,
        "Contacts retain recorded strand order; diamonds mark noncanonical pairing."
        if fields
        else "All compared coordinates are constant in this collection.",
        anchor="start",
    )
    height = y + 8
    svg.set("viewBox", f"0 0 {width} {height}")
    svg.set("height", f"{height}pt")
    background.set("height", str(height))
    return cast(bytes, ET.tostring(svg, encoding="utf-8", xml_declaration=True))
