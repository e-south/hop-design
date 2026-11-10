"""Typed scientific feature groups; the exact mixed comparison record stays intact."""

import json
from math import isfinite
from textwrap import wrap
from typing import Any, cast
from xml.etree import ElementTree as ET

GROUPS = {"shape": "Geometry", "sequences": "Contacts and loop", "interfaces": "Assembly ends"}


def render_comparison_vector(packet: dict[str, Any], *, width_pt: float = 504) -> bytes:
    """Display named scientific types, with no numerical-array implication."""
    if isinstance(width_pt, bool) or not isfinite(width_pt) or not 180 <= width_pt <= 720:
        raise ValueError("Feature panel width must be 180 to 720 points.")
    fields = packet["vector"]
    font = 8.5
    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": f"{width_pt:g}pt",
            "data-preparation-id": packet["identity"],
            "data-comparison-display": "typed-features",
            "role": "img",
        },
    )
    ET.SubElement(svg, "title").text = (
        "Mixed-type molecular comparison features. Geometry, ordered contacts and words retain "
        "their scientific units and meanings; pairwise dissimilarity uses the unchanged "
        "recorded policy."
    )
    ET.SubElement(svg, "metadata").text = json.dumps(
        packet, ensure_ascii=False, separators=(",", ":")
    )
    background = ET.SubElement(svg, "rect", {"width": str(width_pt), "fill": "white"})

    def text(
        parent: ET.Element,
        x: float,
        y: float,
        value: str,
        *,
        mono: bool = False,
        anchor: str = "start",
        size: float = font,
        attrs: dict[str, str] | None = None,
    ) -> ET.Element:
        node = ET.SubElement(
            parent,
            "text",
            {
                "x": str(x),
                "y": str(y),
                "font-size": str(size),
                "font-family": "Courier New,monospace" if mono else "Arial,sans-serif",
                "fill": "#253b40",
                "text-anchor": anchor,
                **(attrs or {}),
            },
        )
        node.text = value
        return node

    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, field in enumerate(fields):
        label = GROUPS.get(field["key"].split(".")[0], "Other features")
        groups.setdefault(label, []).append((index, field))
    columns = len(groups) if width_pt >= 480 else 1
    column_width = (width_pt - 16 - (columns - 1) * 12) / max(1, columns)
    y = 12.0
    bottom = y
    if not fields:
        text(svg, 8, y, "All compared features are constant in this collection.")
        bottom = y + 12
    for group_no, (label, members) in enumerate(groups.items()):
        x = 8 + group_no * (column_width + 12) if columns > 1 else 8
        top = 12.0 if columns > 1 else y
        group = ET.SubElement(svg, "g", {"data-feature-group": label})
        text(group, x, top, label, size=10.5, attrs={"font-weight": "600"})
        local_y = top + 17
        row_y, row_bottom = local_y, local_y
        contact_features = [f for _, f in members if f.get("encoding") == "contacts"]
        paired = (
            columns == 1
            and len(contact_features) == 2
            and all(len(f["value"]) <= 20 for f in contact_features)
        )
        for index, feature in members:
            item_x, item_width = x, column_width
            if paired and feature.get("encoding") == "contacts":
                contact_no = contact_features.index(feature)
                if contact_no == 0:
                    row_y = local_y
                item_x += contact_no * column_width * 0.62
                item_width = column_width * (0.60 if contact_no == 0 else 0.38)
                local_y = row_y
            elif paired:
                local_y = max(local_y, row_bottom)
            item = ET.SubElement(
                group,
                "g",
                {
                    "data-feature": feature["key"],
                    "data-vector-index": str(index),
                    "data-encoded": json.dumps(
                        feature["encoded"], ensure_ascii=False, separators=(",", ":")
                    ),
                },
            )
            ET.SubElement(item, "title").text = json.dumps(feature, ensure_ascii=False)
            if feature.get("encoding") == "contacts":
                text(item, item_x, local_y, feature["label"])
                local_y += 13
                contacts = feature["value"]
                capacity = max(1, int((item_width - 8) / 5.1))
                for start in range(0, len(contacts), capacity):
                    for j, (upper, lower, kind) in enumerate(contacts[start : start + capacity]):
                        cx = item_x + 4 + j * 5.1
                        pair = ET.SubElement(
                            item,
                            "g",
                            {"data-contact-class": kind, "data-contact-index": str(start + j)},
                        )
                        text(
                            pair,
                            cx,
                            local_y,
                            upper,
                            mono=True,
                            anchor="middle",
                            attrs={"data-contact-row": "source"},
                        )
                        text(
                            pair,
                            cx,
                            local_y + 18,
                            lower,
                            mono=True,
                            anchor="middle",
                            attrs={"data-contact-row": "paired"},
                        )
                        d = (
                            f"M{cx},{local_y + 2} V{local_y + 10}"
                            if kind == "watson_crick"
                            else f"M{cx},{local_y + 2} l2,4 l-2,4 l-2,-4 Z"
                        )
                        ET.SubElement(
                            pair,
                            "path",
                            {
                                "d": d,
                                "stroke": "#70838A",
                                "stroke-width": ".65",
                                "fill": "none",
                                "data-contact-glyph": "line"
                                if kind == "watson_crick"
                                else "diamond",
                            },
                        )
                    local_y += 30
                row_bottom = max(row_bottom, local_y)
            else:
                value = feature["value"]
                value = "".join(value) if isinstance(value, list | tuple) else str(value)
                if feature.get("unit"):
                    value += " " + feature["unit"]
                reserved = max(36, len(value) * 5.1 + 8)
                lines = wrap(
                    feature["label"],
                    width=max(5, int((column_width - reserved) / 4.8)),
                    break_long_words=False,
                )
                for i, line in enumerate(lines):
                    text(item, x, local_y + i * 10, line)
                text(item, x + column_width, local_y, value, mono=True, anchor="end")
                local_y += max(14, len(lines) * 10 + 4)
        bottom = max(bottom, local_y)
        if columns == 1:
            y = local_y + 5
    text(
        svg,
        8,
        bottom + 8,
        "Contact rows retain recorded order; diamonds mark noncanonical pairing."
        if width_pt >= 480
        else "Contact rows retain recorded strand order.",
        size=8,
    )
    if width_pt < 480:
        text(svg, 8, bottom + 19, "Diamonds mark noncanonical pairing.", size=8)
    height = bottom + (27 if width_pt < 480 else 16)
    svg.set("viewBox", f"0 0 {width_pt:g} {height:g}")
    svg.set("height", f"{height:g}pt")
    background.set("height", str(height))
    return cast(bytes, ET.tostring(svg, encoding="utf-8", xml_declaration=True))
