"""One publication-scale SVG for complete-path survey browsing and static export."""

import json
from dataclasses import asdict
from itertools import groupby
from textwrap import wrap
from typing import Any, cast
from xml.etree import ElementTree as ET

from ..molecular.primitives.typography import text_width
from ..presentation.figure_profile import PUBLICATION_FIGURE, FigureProfile
from ..presentation.regions import REGIONS, teaching_region
from .display_projection import append_display_metadata
from .guide import plot_context
from .layout import (
    FONT,
    STATES,
    WIDTH,
    heading_lines,
    node_geometry,
    plot_layout,
    visible_labels,
)
from .presentation import present_choices
from .traces import trace_commands

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def _element(parent: ET.Element, tag: str, text: str | None = None, **attrs: Any) -> ET.Element:
    item = ET.SubElement(
        parent, f"{{{SVG}}}{tag}", {k.replace("_", "-"): str(v) for k, v in attrs.items()}
    )
    item.text = text
    return item


def render_survey_plot(
    choices: dict[str, Any],
    *,
    selected_identity: str | None = None,
    include_traces: bool = True,
    profile: FigureProfile = PUBLICATION_FIGURE,
    display_axes: tuple[str, ...] | None = None,
) -> bytes:
    """Render admitted coordinates; never manufacture cross-axis combinations."""
    presentation = present_choices(choices, display_axes=display_axes)
    layout = plot_layout(presentation, profile=profile)
    axes, frame = layout.axes, layout.frame
    width, font = profile.width, profile.axis_font
    root = ET.Element(
        f"{{{SVG}}}svg",
        {
            "viewBox": f"0 0 {width} {layout.height:g}",
            "data-axis-frame": json.dumps(asdict(frame), separators=(",", ":")),
            "width": "7in",
            "font-size": str(font),
            "font-family": "Arial, Helvetica, sans-serif",
            "role": "group",
            "aria-label": "Complete paths through declared molecular parameters",
        },
    )
    background = _element(root, "rect", x=0, y=0, width=width, fill="white")
    if not axes:
        _element(
            root,
            "text",
            "No varying coordinates in this view.",
            x=width / 2,
            y=frame.height / 2,
            text_anchor="middle",
            fill="#53696d",
        )
    _element(
        root,
        "metadata",
        json.dumps(
            {k: choices[k] for k in ("request_digest", "snapshot_digest", "query_digest")},
            sort_keys=True,
        ),
    )
    append_display_metadata(root, presentation)
    query_keys = {p["key"] for p in choices["query"]["parameters"]}
    context = [a["key"] for a in presentation["detail"] if a["key"] in query_keys]
    root.set("data-context-parameters", json.dumps(context))
    root.set("data-fixed-parameters", json.dumps([a["key"] for a in presentation["fixed"]]))
    root.set(
        "data-observed-constants",
        json.dumps([a["key"] for a in presentation["observed_constants"]]),
    )
    root.set("data-projected-traces", str(len(presentation["traces"])))
    for (band, region), members in groupby(
        axes,
        key=lambda m: (m["band"], teaching_region(m["definition"]["neighborhood"])),
    ):
        columns = list(members)
        left = columns[0]["x"] - columns[0]["width"] / 2 - 3
        right = columns[-1]["x"] + columns[-1]["width"] / 2 + 3
        label, color = REGIONS[region]
        region_labels = (
            label.split()
            if profile.width < WIDTH and text_width(label, font) > right - left - 8
            else [label]
        )
        _element(
            root,
            "rect",
            x=left,
            y=band * frame.height + 4,
            width=right - left,
            height=len(region_labels) * font + 8,
            rx=3,
            fill=color,
            fill_opacity=0.5,
            data_axis_region=region,
        )
        for index, line in enumerate(region_labels):
            _element(
                root,
                "text",
                line,
                x=(left + right) / 2,
                y=band * frame.height + frame.region_baseline + index * font,
                text_anchor="middle",
                fill="#263b40",
            )
    for m in axes:
        _element(
            root,
            "line",
            x1=m["x"],
            x2=m["x"],
            y1=frame.top + m["band"] * frame.height,
            y2=frame.bottom + m["band"] * frame.height,
            stroke="#c0cacc",
            stroke_width=0.8,
        )
    for group in sorted(
        presentation["traces"] if include_traces else [],
        key=lambda g: any(p["materialized_realization_id"] == selected_identity for p in g),
    ):
        selected = any(p["materialized_realization_id"] == selected_identity for p in group)
        matching = any(p["matches"] for p in group)
        trace = _element(
            root,
            "path",
            d=trace_commands(axes, group[0]),
            fill="none",
            stroke="#a55236" if selected else "#4b8b83" if matching else "#aab8bb",
            stroke_width=2.3 if selected else 0.8,
            opacity=0.95 if selected else 0.3 if matching else 0.09,
            data_members=json.dumps([p["materialized_realization_id"] for p in group]),
            data_selected=str(selected).lower(),
            tabindex=0,
            role="button",
        )
        _element(
            trace,
            "title",
            f"{len(group)} exact preparations; {sum(p['matches'] for p in group)} match. "
            "Compatibility, not chronology.",
        )
    total, labeled = 0, 0
    for m in axes:
        axis, x, positions = m["definition"], m["x"], m["y"]
        offset = m["band"] * frame.height
        if axis["kind"] == "numeric" and len(positions) > 1:
            _element(
                root,
                "rect",
                x=x - 12,
                y=frame.top + offset,
                width=7,
                height=frame.bottom - frame.top,
                fill="#ffffff",
                fill_opacity=0,
                data_brush_axis=axis["key"],
                data_positions=json.dumps(list(positions.items())),
                aria_label=f"Brush {axis['label']}",
            )
        container = _element(
            root,
            "g",
            data_axis=axis["key"],
            data_parameter=axis["key"],
            data_band=m["band"],
            data_region=teaching_region(axis["neighborhood"]),
        )
        title = _element(
            container,
            "g",
            data_axis_title=axis["key"],
            tabindex=0,
            role="button",
            aria_label=f"Choose {axis['label']}",
        )
        headings = heading_lines(axis, profile=profile)
        for i, line in enumerate(headings):
            _element(
                title,
                "text",
                line,
                x=x,
                y=offset + frame.heading_y + i * font,
                text_anchor="middle",
                fill="#263b40",
            )
        unit = {"positions": "pos", "contacts": "ct"}.get(axis["unit"], axis["unit"])
        _element(
            title,
            "text",
            unit,
            x=x,
            y=offset + frame.heading_y + 3 + len(headings) * font,
            text_anchor="middle",
            fill="#617277",
        )
        _element(title, "title", f"{axis['symbol']}: {axis['label']}. {axis['measurement']}")
        selected_values = {
            p["values"][axis["key"]]
            for p in choices["paths"]
            if p["materialized_realization_id"] == selected_identity
        }
        labels = visible_labels(axis, positions, choices, selected_values, profile=profile)
        predicate = next(
            (p for p in choices["query"]["parameters"] if p["key"] == axis["key"]), None
        )
        # Dense unlabeled ticks must be painted before the readable value cells.
        # Keep every node and its exact position/interaction target.
        for node in sorted(axis["nodes"], key=lambda n: n["value"] in labels):
            value, state = node["value"], node["state"]
            y, (stroke, fill, dash) = positions[value], STATES[state]
            pinned = False
            if predicate is not None:
                pinned = (
                    value in predicate["values"]
                    if predicate.get("values") is not None
                    else (predicate["minimum"] <= value <= predicate["maximum"])
                )
            node_group = _element(
                container,
                "g",
                data_node_value=json.dumps(value),
                data_support_state=state,
                data_parameter=axis["key"],
                data_y=y,
                data_pinned=str(pinned).lower(),
                tabindex=0,
                role="button",
            )
            _element(
                node_group,
                "title",
                f"{axis['label']}: {node['label']}; {state}; "
                f"{node['conditional_preparations']} preparations under the other predicates.",
            )
            total += 1
            if pinned and value not in labels:
                _element(
                    node_group,
                    "rect",
                    x=x + 7,
                    y=y - 2,
                    width=4,
                    height=4,
                    fill="#146b9b",
                    data_query_pin="true",
                )
            _element(
                node_group,
                "line",
                x1=x - 4,
                x2=x + 4,
                y1=y,
                y2=y,
                stroke=stroke,
                stroke_width=1.2,
                stroke_dasharray=dash,
                data_node_mark="true",
                data_support_state=state,
            )
            if value not in labels:
                continue
            labeled += 1
            geometry = node_geometry(axis, node, profile=profile)
            lines, height, node_width = geometry["lines"], geometry["height"], geometry["width"]
            _element(
                node_group,
                "rect",
                x=x - node_width / 2,
                y=y - height / 2,
                width=node_width,
                height=height,
                rx=3,
                fill=fill,
                stroke=stroke,
                stroke_dasharray=dash,
                stroke_width=0.8,
                data_node_label="true",
            )
            for j, text in enumerate(lines):
                _element(
                    node_group,
                    "text",
                    text,
                    x=x,
                    y=y + (j - (len(lines) - 1) / 2) * font + font * 0.35,
                    text_anchor="middle",
                    fill="#263b40",
                    data_node_label="true",
                )
            if pinned:
                _element(
                    node_group,
                    "rect",
                    x=x - 3.5,
                    y=y + height / 2 + 1,
                    width=7,
                    height=2,
                    fill="#146b9b",
                    data_query_pin="true",
                )
    root.set("data-landscape-frame", f"0 0 {width} {layout.height:g}")
    caption = _element(root, "g", data_plot_context="true")
    y = layout.height + font

    def note(text: str, **attrs: Any) -> None:
        nonlocal y
        for line in wrap(
            text, width=round(91 * width / WIDTH * FONT / font), break_on_hyphens=False
        ):
            _element(caption, "text", line, x=26, y=y, fill="#53696d", **attrs)
            y += font + 5

    for text, attributes in plot_context(
        presentation, choices.get("fully_enumerated", False), len(context)
    ):
        note(text, **attributes)
    root.set("data-domain-values", str(total))
    root.set("data-visible-labels", str(labeled))
    height = y + 8
    background.set("height", str(height))
    root.set("viewBox", f"0 0 {width} {height}")
    root.set("height", f"{7 * height / width}in")
    return cast(bytes, ET.tostring(root, encoding="utf-8"))
