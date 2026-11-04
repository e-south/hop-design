"""Publication composition and complete domain key for the shared survey plot."""

import csv
import json
from dataclasses import replace
from io import StringIO
from textwrap import wrap
from typing import Any, cast
from xml.etree import ElementTree as ET

from ..presentation.figure_profile import PUBLICATION_FIGURE, FigureProfile
from .figure_layout import add_layout_links, figure_layout, plot_geometry, teaching_geometry
from .layout import FONT, WIDTH, node_lines
from .plot import SVG, _element


def domain_csv(choices: dict[str, Any]) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        (
            "key",
            "symbol",
            "parameter",
            "stage",
            "unit",
            "value",
            "label",
            "display",
            "state",
            "supported_preparations",
            "conditional_preparations",
        )
    )
    for axis in choices["axes"]:
        for node in axis["nodes"]:
            writer.writerow(
                (
                    axis["key"],
                    axis["symbol"],
                    axis["label"],
                    axis["stage"],
                    axis["unit"],
                    node["value"],
                    node["label"],
                    "".join(node_lines(axis, node)),
                    node["state"],
                    node["supported_preparations"],
                    node["conditional_preparations"],
                )
            )
    return output.getvalue().encode()


def compose_figure(
    key: bytes,
    plot: bytes,
    choices: dict[str, Any],
    *,
    selected_identity: str | None = None,
    profile: FigureProfile = PUBLICATION_FIGURE,
) -> bytes:
    """Stack the schematic and exact same plot used by the browser; no HTML controls."""
    root = ET.Element(
        f"{{{SVG}}}svg",
        {
            "width": "7in",
            "font-family": "Arial, Helvetica, sans-serif",
            "font-size": str(profile.axis_font),
        },
    )
    background = _element(root, "rect", width=profile.width, fill="white")
    documents = [ET.fromstring(component) for component in (key, plot)]
    layout_profile = profile
    fit_content = not profile.stable_teaching_slot and any(
        element.get("data-display-projection") for element in documents[1]
    )
    if fit_content:
        # A curated static plate fits its actual molecule. Interactive profiles
        # keep stable teaching slots so selections do not move the trace.
        layout_profile = replace(profile, minimum_teaching_slot=0, teaching_slot_step=1)
    spec = figure_layout(
        teaching_geometry(documents[0], fit_content=fit_content),
        plot_geometry(documents[1]),
        profile=layout_profile,
    )
    root.set("data-figure-layout", json.dumps(spec, separators=(",", ":")))
    for name, document in zip(("hairpin", "trace"), documents, strict=True):
        if document.get("data-landscape-frame"):
            context = document.find(f"{{{SVG}}}g[@data-plot-context='true']")
            if context is not None:
                document.remove(context)
        box = spec[name]
        frame_x, frame_y, frame_width, frame_height = map(float, box["frame"].split())
        # Explicit user-space transforms keep SVG and PDF coordinates identical.
        # Nested SVG viewports acquire an extra pixel-to-point scale in svglib.
        group = _element(
            root,
            "g",
            transform=(
                f"translate({box['x']} {box['y']}) "
                f"scale({box['width'] / frame_width} {box['height'] / frame_height}) "
                f"translate({-frame_x} {-frame_y})"
            ),
            data_panel_frame=box["frame"],
            data_figure_panel=name,
        )
        for attribute in (
            "data-teaching-resolution",
            "data-preparation-id",
            "font-size",
            "font-family",
        ):
            if attribute in document.attrib:
                group.set(attribute, document.attrib[attribute])
        for child in document:
            if child.tag.endswith("}rect") and child.get("fill") == "white":
                child.set("fill", "none")
        group.extend(document)
    add_layout_links(root, spec)
    y = float(spec["frame"].split()[3]) + 12
    family_view = documents[1].get("data-layout") in {"mosaic", "feature_map"}
    legend = (
        "Filled: eligible · hollow: outside filter · dark outline: selected. "
        "Numbers count coincident products; \u00d7N counts preparations."
        if family_view
        else "Filled: supported · hollow: outside filter · dotted: unresolved · "
        "red dashed: excluded. "
        "Orange trace: selected preparation. Shaded connectors locate molecular features."
    )
    for line in wrap(
        legend,
        width=round(91 * profile.width / WIDTH * FONT / profile.axis_font),
        break_on_hyphens=False,
    ):
        _element(root, "text", line, x=26, y=y + 8)
        y += profile.axis_font + 5
    height = y + 8
    background.set("height", str(height))
    root.set("viewBox", f"0 0 {profile.width} {height}")
    root.set("height", f"{7 * height / profile.width}in")
    return cast(bytes, ET.tostring(root, encoding="utf-8"))
