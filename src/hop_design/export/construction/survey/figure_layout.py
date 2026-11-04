"""Measured teaching/trace composition shared by SVG export and inspection.

Coordinates describe drawing placement, never molecular correspondence. The
teaching slot grows in continuation rows; ordinary selections retain its bounds.
"""

import json
from math import ceil
from typing import Any
from xml.etree import ElementTree as ET

from ..presentation.figure_profile import PUBLICATION_FIGURE, FigureProfile

SVG = "http://www.w3.org/2000/svg"
AXIS_LANDING_Y = 0


def teaching_geometry(content: bytes | ET.Element, *, fit_content: bool = False) -> dict[str, Any]:
    root = ET.fromstring(content) if isinstance(content, bytes) else content
    return {
        "frame": root.get("data-content-frame", root.attrib["viewBox"])
        if fit_content
        else root.attrib["viewBox"],
        "anchors": {
            e.attrib["data-parameter-anchor"]: {
                "box": json.loads(e.attrib["data-anchor-box"]),
                "regions": json.loads(e.get("data-anchor-regions", "null")),
            }
            for e in root.iter()
            if e.get("data-parameter-anchor") and e.get("data-anchor-box")
        },
    }


def plot_geometry(content: bytes | ET.Element) -> dict[str, Any]:
    root = ET.fromstring(content) if isinstance(content, bytes) else content
    anchors = {}
    for axis in root.iter():
        if axis.get("data-axis") and axis.get("data-band") == "0":
            title = next((e for e in axis if e.get("data-axis-title")), None)
            label = None if title is None else next(iter(title), None)
            if label is not None:
                anchors[axis.attrib["data-axis"]] = [
                    float(label.attrib["x"]),
                    AXIS_LANDING_Y,
                ]
    return {"frame": root.get("data-landscape-frame", root.attrib["viewBox"]), "anchors": anchors}


def figure_layout(
    teaching: dict[str, Any], plot: dict[str, Any], *, profile: FigureProfile = PUBLICATION_FIGURE
) -> dict[str, Any]:
    kx, ky, kw, kh = map(float, teaching["frame"].split())
    px, py, pw, ph = map(float, plot["frame"].split())
    canvas_width = profile.width
    ks, ps = canvas_width / kw, canvas_width / pw
    step = profile.teaching_slot_step
    slot = max(profile.minimum_teaching_slot, ceil(kh * ks / step) * step)
    top = (slot - kh * ks) / 2
    trace_y = slot + profile.teaching_trace_gap
    links, origins = [], []
    for parameter, anchor in teaching["anchors"].items():
        if parameter not in plot["anchors"]:
            continue
        tx, ty = plot["anchors"][parameter]
        tx, ty = (tx - px) * ps, trace_y + (ty - py) * ps
        x, y, width, height = anchor["box"]
        regions = anchor["regions"] or [anchor["box"]]
        if len(regions) == 1 and width <= 18 and height <= 24:
            origins.append(
                {
                    "parameter": parameter,
                    "x": (x - kx - 2) * ks,
                    "y": top + (y - ky - 3) * ks,
                    "width": (width + 4) * ks,
                    "height": (height + 6) * ks,
                    "rx": 3,
                }
            )
        for x, y, width, height in regions:
            sy = top + (y - ky + height) * ks
            links.append(
                {
                    "parameter": parameter,
                    "points": f"{(x - kx) * ks},{sy} {(x - kx + width) * ks},{sy} "
                    f"{tx + 16},{ty} {tx - 16},{ty}",
                }
            )
    return {
        "frame": f"0 0 {canvas_width} {trace_y + ph * ps:g}",
        "hairpin": {
            "frame": teaching["frame"],
            "x": 0,
            "y": top,
            "width": canvas_width,
            "height": kh * ks,
        },
        "trace": {
            "frame": plot["frame"],
            "x": 0,
            "y": trace_y,
            "width": canvas_width,
            "height": ph * ps,
        },
        "links": links,
        "origins": origins,
    }


def add_layout_links(root: ET.Element, spec: dict[str, Any]) -> None:
    fans = ET.Element(f"{{{SVG}}}g", {"data-teaching-fans": "true", "pointer-events": "none"})
    root.insert(1, fans)
    for link in spec["links"]:
        group = ET.SubElement(
            fans,
            f"{{{SVG}}}g",
            {"data-parameter-link": link["parameter"], "data-parameter": link["parameter"]},
        )
        ET.SubElement(
            group,
            f"{{{SVG}}}polygon",
            {
                "points": link["points"],
                "fill": "#679a9c",
                "fill-opacity": "0.07",
                "stroke": "#679a9c",
                "stroke-opacity": "0.28",
                "stroke-width": "0.8",
            },
        )
    for origin in spec["origins"]:
        ET.SubElement(
            root,
            f"{{{SVG}}}rect",
            {
                **{k: str(v) for k, v in origin.items() if k != "parameter"},
                "data-parameter-origin": origin["parameter"],
                "fill": "none",
                "stroke": "#182B34",
                "stroke-width": "2.2",
                "pointer-events": "none",
            },
        )
