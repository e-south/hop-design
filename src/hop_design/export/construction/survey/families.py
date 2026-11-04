"""Compact exact-product atlas; positions have declared meaning or are explicitly packing."""

import json
from collections import defaultdict
from math import ceil, sqrt
from textwrap import wrap
from typing import Any, cast
from xml.etree import ElementTree as ET

from .layout import FONT, WIDTH
from .plot import SVG, _element

INK, ACCENT, PALE, MUTED = "#213c43", "#216e72", "#e6f0ee", "#71858a"


def _text(
    parent: ET.Element,
    text: str,
    x: float,
    y: float,
    *,
    anchor: str = "start",
    weight: str = "normal",
    fill: str = INK,
) -> ET.Element:
    return _element(
        parent, "text", text, x=x, y=y, text_anchor=anchor, font_weight=weight, fill=fill
    )


def _mark(
    parent: ET.Element,
    products: list[dict[str, Any]],
    x: float,
    y: float,
    selected: str | None,
    *,
    label: bool = False,
    label_width: float = 228,
) -> ET.Element:
    identities = [p["identity"] for p in products]
    preparations = [i for p in products for i in p["preparations"]]
    eligible = any(p["eligible_preparations"] for p in products)
    active = selected in preparations
    group = _element(
        parent,
        "g",
        data_products=json.dumps(identities),
        data_preparations=json.dumps(preparations),
        data_selected=str(active).lower(),
        tabindex="0",
        role="button",
        aria_label="; ".join(p["label"] for p in products),
    )
    title = "; ".join(f"{p['label']} ({len(p['preparations'])} preparations)" for p in products)
    _element(group, "title", title)
    _element(
        group,
        "circle",
        cx=x,
        cy=y,
        r=17 if len(products) > 1 else 12,
        fill=ACCENT if eligible else "white",
        stroke=INK if active else ACCENT,
        stroke_width=5 if active else 2,
    )
    if len(products) > 1:
        _text(
            group,
            str(len(products)),
            x,
            y + FONT * 0.33,
            anchor="middle",
            fill="white" if eligible else INK,
        )
    if label:
        lines = wrap(products[0]["label"], width=max(8, int(label_width / (FONT * 0.54))))
        for index, line in enumerate(lines):
            _text(group, line, x + 22, y + FONT * 0.33 + index * (FONT + 3))
        if len(preparations) > 1:
            _text(
                group,
                f"\u00d7{len(preparations)}",
                x + 22,
                y + (len(lines) + 0.6) * FONT,
                fill=MUTED,
            )
    return group


def _family_target(
    parent: ET.Element,
    families: list[dict[str, Any]],
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    label = "Explore family: " + "; ".join(f["label"] for f in families)
    target = _element(
        parent,
        "rect",
        x=x,
        y=y,
        width=width,
        height=height,
        rx=12,
        fill=PALE,
        stroke="#a9c3c0",
        stroke_width=2,
        data_family_ids=json.dumps([f["identity"] for f in families]),
        tabindex="0",
        role="button",
        aria_label=label,
    )
    _element(target, "title", label + ". Filters complete preparations without selecting one.")


def _mosaic(root: ET.Element, atlas: dict[str, Any], selected: str | None) -> float:
    families = atlas["families"]
    if not families:
        _text(root, "No recorded products in this edition", WIDTH / 2, 130, anchor="middle")
        return 220
    columns = min(4, len(families), max(1, ceil(sqrt(len(families) * 2))))
    width = (WIDTH - 48 - (columns - 1) * 18) / columns
    by_id = {p["identity"]: p for p in atlas["products"]}
    cards = []
    for family in families:
        products = [by_id[i] for i in family["products"]]
        labelled = len(atlas["products"]) <= 12 and width >= 260
        across = max(1, int((width - 44) / (350 if labelled else 38)))
        cell_width = (width - 44) / across
        characters = max(8, int((cell_width - 36) / (FONT * 0.54)))
        line_count = max(len(wrap(p["label"], width=characters)) for p in products)
        row_step = max(66, (line_count + 1) * (FONT + 3)) if labelled else 38
        height = 96 + ceil(len(products) / across) * row_step
        cards.append((family, products, labelled, across, row_step, height))
    y = 66
    for start in range(0, len(cards), columns):
        row = cards[start : start + columns]
        height = max(card[-1] for card in row)
        for col, (family, products, labelled, across, step, _) in enumerate(row):
            x = 24 + col * (width + 18)
            group = _element(root, "g", data_family=family["identity"])
            _family_target(group, [family], x, y, width, height)
            lines = wrap(family["label"], width=max(12, int((width - 32) / (FONT * 0.54))))
            for line_no, line in enumerate(lines[:2]):
                label = _text(group, line, x + 16, y + 30 + line_no * (FONT + 4), weight="bold")
                label.set("pointer-events", "none")
            for i, product in enumerate(products):
                _mark(
                    group,
                    [product],
                    x + 28 + (i % across) * ((width - 44) / across if labelled else 38),
                    y + 102 + (i // across) * step,
                    selected,
                    label=labelled,
                    label_width=(width - 44) / across - 36,
                )
        y += height + 18
    _text(
        root,
        "Grouped by recorded structure · position is packing, not molecular distance",
        24,
        y + 16,
        fill=MUTED,
    )
    return y + 40


def _feature_map(root: ET.Element, atlas: dict[str, Any], selected: str | None) -> float:
    keys = [atlas["layout"][a] for a in ("x", "y")]
    definitions = {d["key"]: d for d in atlas["features"]}
    values = [[p["features"][key][0] for p in atlas["products"]] for key in keys]
    low = [float(min(v)) for v in values]
    high = [float(max(v)) for v in values]
    left, right, top, bottom = 130, WIDTH - 100, 86, 338

    def position(value: float, axis: int) -> float:
        fraction = (value - low[axis]) / (high[axis] - low[axis])
        return left + fraction * (right - left) if axis == 0 else bottom - fraction * (bottom - top)

    _element(
        root,
        "path",
        d=f"M {left} {top - 10} V {bottom} H {right + 20}",
        fill="none",
        stroke=MUTED,
        stroke_width=2,
    )
    for axis, key in enumerate(keys):
        ticks = sorted(set(values[axis]))
        if len(ticks) > 8:
            ticks = sorted({ticks[round(i * (len(ticks) - 1) / 7)] for i in range(8)})
        for tick in ticks:
            v = position(tick, axis)
            if axis == 0:
                _text(root, str(tick), v, bottom + 54, anchor="middle")
            else:
                _text(root, str(tick), left - 44, v + FONT * 0.33, anchor="end")
                _element(
                    root, "path", d=f"M {left} {v} H {right}", stroke="#e6eaea", stroke_width=1
                )
        label = definitions[key]["label"] + f" ({definitions[key]['unit']})"
        if axis == 0:
            _text(root, label, (left + right) / 2, bottom + 104, anchor="middle", weight="bold")
        else:
            _text(root, label, left, 58, weight="bold")
    groups = defaultdict(list)
    for product in atlas["products"]:
        groups[tuple(product["features"][key][0] for key in keys)].append(product)
    for coordinates, products in sorted(groups.items()):
        x, y = position(coordinates[0], 0), position(coordinates[1], 1)
        families = [
            f for f in atlas["families"] if any(p["family_id"] == f["identity"] for p in products)
        ]
        _family_target(root, families, x - 26, y - 26, 52, 52)
        _mark(root, products, x, y, selected)
    root.set("data-x-parameter", keys[0])
    root.set("data-y-parameter", keys[1])
    return 472


def render_molecular_families(
    atlas: dict[str, Any], *, selected_identity: str | None = None, layout: str = "auto"
) -> bytes:
    if layout not in {"auto", "feature_map", "mosaic"}:
        raise ValueError("Unknown molecular-family layout.")
    kind = atlas["layout"]["kind"] if layout == "auto" else layout
    if kind == "feature_map" and atlas["layout"]["kind"] != "feature_map":
        raise ValueError("A feature map requires two varying recorded dimensions; use the mosaic.")
    root = ET.Element(
        f"{{{SVG}}}svg",
        {
            "width": "7in",
            "font-family": "Arial, Helvetica, sans-serif",
            "font-size": str(FONT),
            "data-layout": kind,
            "role": "img",
        },
    )
    _element(root, "title", "Exact molecular products and their complete preparations")
    background = _element(root, "rect", width=WIDTH, fill="white")
    count = sum(bool(p["eligible_preparations"]) for p in atlas["products"])
    _text(
        root, f"{count} available / {len(atlas['products'])} recorded products", 24, 28, fill=MUTED
    )
    height = (
        _feature_map(root, atlas, selected_identity)
        if kind == "feature_map"
        else _mosaic(root, atlas, selected_identity)
    )
    root.set("viewBox", f"0 0 {WIDTH} {height}")
    root.set("height", f"{7 * height / WIDTH:.5f}in")
    background.set("height", str(height))
    return cast(bytes, ET.tostring(root, encoding="utf-8", xml_declaration=True))
