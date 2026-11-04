"""The same compact distribution strip for browser context and figure packets."""

from typing import Any, cast
from xml.etree import ElementTree as ET

from .families import ACCENT, INK, MUTED
from .plot import SVG, _element


def render_choice_distributions(
    distributions: list[dict[str, Any]], *, selected_values: dict[str, Any] | None = None
) -> bytes:
    root = ET.Element(
        f"{{{SVG}}}svg",
        {
            "viewBox": "0 0 480 78",
            "width": "480",
            "height": "78",
            "role": "img",
            "font-family": "Arial, Helvetica, sans-serif",
            "font-size": "13",
            "fill": INK,
        },
    )
    _element(
        root, "title", "Recorded geometry; counts describe preparations, not biological diversity"
    )
    if not distributions:
        return cast(bytes, ET.tostring(root, encoding="utf-8"))
    total = distributions[0]["denominator"]
    _element(
        root,
        "text",
        f"Preparations: {total['eligible']} eligible / {total['recorded']} recorded",
        x=0,
        y=13,
        fill=MUTED,
    )
    for i, distribution in enumerate(distributions[:2]):
        x, bins = 240 * i, distribution["bins"]
        selected = (selected_values or {}).get(distribution["key"])
        title = f"{distribution['label']} ({distribution['unit']})"
        group = _element(root, "g", data_parameter=distribution["key"])
        _element(group, "text", title, x=x, y=32)
        _element(
            group,
            "title",
            f"{title}; {distribution['stage']}. "
            "Pale: recorded; teal: eligible; orange: inspected. "
            f"{distribution['missing']['recorded']} recorded values missing.",
        )
        if not bins:
            _element(group, "text", "Not recorded", x=x, y=60, fill=MUTED)
            continue
        low, high = bins[0]["value"], bins[-1]["value"]
        peak = max(b["recorded"] for b in bins)
        width = min(28, 180 / len(bins))
        for item in bins:
            cx = x + 100 if high == low else x + 14 + (item["value"] - low) / (high - low) * 190
            node = _element(
                group,
                "g",
                data_value=str(item["value"]),
                data_selected=str(item["value"] == selected).lower(),
            )
            _element(
                node,
                "title",
                f"{item['value']} {distribution['unit']}: "
                f"{item['eligible']} eligible / {item['recorded']} recorded preparations",
            )
            for count, fill in ((item["recorded"], "#d5dfdf"), (item["eligible"], ACCENT)):
                height = 18 * count / peak
                _element(
                    node,
                    "rect",
                    x=cx - width / 2,
                    y=57 - height,
                    width=width,
                    height=height,
                    rx=2,
                    fill=fill,
                )
            if item["value"] == selected:
                _element(node, "path", d=f"M {cx} 36 V 59", stroke="#ae5928", stroke_width=2)
            if len(bins) <= 6 or item["value"] in {low, high, selected}:
                _element(node, "text", str(item["value"]), x=cx, y=73, text_anchor="middle")
    return cast(bytes, ET.tostring(root, encoding="utf-8"))
