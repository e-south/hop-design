"""One inspectable preparation per mark over frozen molecular coordinates."""

import json
from collections import defaultdict
from math import sqrt
from typing import Any, cast
from xml.etree import ElementTree as ET

from hop_design.models.construction.variants.landscape import MolecularLandscape

from .color import MolecularColors
from .layout import FONT, WIDTH
from .plot import SVG, _element

INK, ACCENT, MUTED = "#213c43", "#216e72", "#71858a"
HEIGHT = 480


def landscape_geometry(landscape: MolecularLandscape) -> dict[str, Any]:
    """Keep every preparation at its frozen molecular comparison position."""
    mark_radius = max(1.6, min(7, 80 / sqrt(max(1, len(landscape.preparations)))))
    positions = {c.comparison_key: c for c in landscape.coordinates}
    grouped = defaultdict(list)
    for preparation in landscape.preparations:
        grouped[preparation.comparison_key].append(preparation)
    points: list[dict[str, Any]] = []
    for key, preparations in sorted(grouped.items()):
        location, count = positions[key], len(preparations)
        x, y = WIDTH / 2 + location.x * 185, HEIGHT / 2 - location.y * 185
        for preparation in sorted(preparations, key=lambda p: p.identity):
            points.append(
                {
                    "identity": preparation.identity,
                    "comparison_key": key,
                    "x": x,
                    "y": y,
                    "center": [x, y],
                    "molecular": [location.x, location.y],
                    "offset": [0.0, 0.0],
                    "coincident": count,
                    "loop": "".join(str(b) for b in preparation.sequences["loop"]),
                }
            )
    frame = [0.0, 0.0, float(WIDTH), float(HEIGHT)]
    if points:
        left = min(p["x"] for p in points) - mark_radius
        right = max(p["x"] for p in points) + mark_radius
        top = min(p["y"] for p in points) - mark_radius
        bottom = max(p["y"] for p in points) + mark_radius
        padding = max(12, max(right - left, bottom - top) * 0.08)
        frame = [
            left - padding,
            top - padding,
            right - left + 2 * padding,
            bottom - top + 2 * padding,
        ]
    return {"points": points, "radius": mark_radius, "frame": frame}


def render_molecular_landscape(
    landscape: MolecularLandscape,
    *,
    eligible: set[str],
    selected_identity: str | None = None,
    colors: MolecularColors | None = None,
) -> bytes:
    identities = {p.identity for p in landscape.preparations}
    if not eligible <= identities or (selected_identity and selected_identity not in identities):
        raise ValueError("Molecular map eligibility and selection must belong to this edition.")
    root = ET.Element(
        f"{{{SVG}}}svg",
        {
            "viewBox": f"0 0 {WIDTH} {HEIGHT}",
            "width": str(WIDTH),
            "height": str(HEIGHT),
            "role": "group",
            "aria-label": "Molecular similarity of complete preparations",
            "font-family": "Arial, Helvetica, sans-serif",
            "font-size": str(FONT),
            "data-landscape-digest": landscape.digest,
        },
    )
    _element(root, "rect", x=0, y=0, width=WIDTH, height=HEIGHT, fill="white")
    if colors is not None:
        if set(colors.colors) != identities:
            raise ValueError("Map colors must cover the exact recorded preparations.")
        root.set("data-color-key", colors.lens.key)
        root.set("data-color-word", colors.lens.word or "")
        _element(
            root,
            "text",
            colors.label + " · Hollow: outside filters",
            x=24,
            y=55,
            fill=MUTED,
            font_size=FONT - 2,
            data_color_legend="true",
        )
    _element(
        root,
        "text",
        f"{len(landscape.preparations)} complete preparations",
        x=24,
        y=34,
        fill=INK,
        font_weight="bold",
        data_map_context="true",
    )
    geometry = landscape_geometry(landscape)
    # Keep the visible cloud light; frozen coordinates and interaction geometry
    # remain independent of the publication mark's size.
    mark_radius = min(1.35, geometry["radius"])
    # Eligible marks remain visible over excluded peers; the pinned preparation
    # is painted last even when it lies outside the current filter.
    points = sorted(
        geometry["points"],
        key=lambda p: (p["identity"] == selected_identity, p["identity"] in eligible),
    )
    for point in points:
        identity, count = point["identity"], point["coincident"]
        active, available = identity == selected_identity, identity in eligible
        color = colors.colors[identity] if colors is not None else ACCENT
        label = f"Loop {point['loop']}; {'eligible' if available else 'outside current filters'}"
        if count > 1:
            label += f"; one of {count} preparations at the same molecular position"
        group = _element(
            root,
            "g",
            tabindex="0",
            role="button",
            aria_label=label,
            data_preparation=identity,
            data_preparations=json.dumps([identity]),
            data_comparison_key=point["comparison_key"],
            data_coincident_count=count,
            data_molecular_x=point["molecular"][0],
            data_molecular_y=point["molecular"][1],
            data_display_dx=point["offset"][0],
            data_display_dy=point["offset"][1],
            data_eligible=str(available).lower(),
            data_selected=str(active).lower(),
        )
        _element(group, "desc", label)
        _element(
            group,
            "circle",
            cx=point["x"],
            cy=point["y"],
            r=2 * mark_radius if active else mark_radius,
            fill=color if available and color is not None else "none",
            fill_opacity=1 if active else 0.28,
            stroke=INK if active else "none" if available else color or MUTED,
            stroke_width=1.5 if active else 0.8,
            stroke_opacity=1 if active else 0.35,
            stroke_dasharray="none" if available else "3 2",
        )
        if color is None:
            r = mark_radius
            _element(
                group,
                "path",
                d=f"M{point['x'] - r:g} {point['y'] - r:g}l{2 * r:g} {2 * r:g}"
                f"M{point['x'] - r:g} {point['y'] + r:g}l{2 * r:g} {-2 * r:g}",
                stroke=MUTED,
                stroke_width=1,
                stroke_opacity=1 if active else 0.35,
                fill="none",
            )
    _element(
        root,
        "text",
        "Nearby: similar scaffold and interfaces · Identical descriptors share a position",
        x=24,
        y=HEIGHT - 14,
        fill=MUTED,
        font_size=FONT - 2,
        data_map_context="true",
    )
    if geometry["points"]:
        root.set("data-map-frame", " ".join(f"{v:g}" for v in geometry["frame"]))
    return cast(bytes, ET.tostring(root, encoding="utf-8", xml_declaration=True))
