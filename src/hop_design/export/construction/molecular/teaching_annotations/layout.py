"""Locate teaching brackets on the same nucleotide geometry as the route."""

import json
from typing import Any
from xml.etree import ElementTree as ET

from ..label_layout import LabelPlacer, coalesce_horizontal
from ..parameter_boundaries import boundary_point
from ..primitives.typography import text_width
from ..printing.panels import base_box
from ..teaching_canvas import TeachingCanvas

SVG = "http://www.w3.org/2000/svg"


def label_backplates(root: ET.Element) -> None:
    """Keep feature-to-axis fans out of measured annotation text, without a legend."""
    for parent in list(root.iter()):
        for child in list(parent):
            if not child.tag.endswith("}text") or not child.get("data-label-box"):
                continue
            x, y, width, height = json.loads(child.attrib["data-label-box"])
            rect = ET.Element(
                f"{{{SVG}}}rect",
                {
                    "x": str(x - 1),
                    "y": str(y - 1),
                    "width": str(width + 2),
                    "height": str(height + 2),
                    "fill": "white",
                    "rx": "2",
                    "data-annotation-backplate": "true",
                    "pointer-events": "none",
                },
            )
            parent.insert(list(parent).index(child), rect)


class OverviewLabels:
    """Measure larger overview labels against nucleotide and annotation bounds."""

    def __init__(
        self, points: dict[tuple[str, int], tuple[float, float]], *, width: int, size: int
    ) -> None:
        self.size = size
        self.placer = LabelPlacer(
            coalesce_horizontal([(x - 10, y - 14, 20, 28) for x, y in points.values()]),
            top=4,
            horizontal_bounds=(8, width - 8),
        )

    @property
    def bottom(self) -> float:
        return max(y + h for _, y, _, h in self.placer.occupied)

    def text(self, parent: ET.Element, x: float, y: float, value: str, **attrs: Any) -> ET.Element:
        feature = attrs.pop("feature_anchor", None)
        size = max(self.size, int(attrs.pop("font_size", self.size)))
        anchor = attrs.pop("text_anchor", "start")
        x -= text_width(value, size) * {"start": 0, "middle": 0.5, "end": 1}[anchor]
        a, b, w, h = self.placer.place(x, y, value, size=size)
        if feature is not None:
            fx, fy = feature
            tx, ty = min(max(fx, a), a + w), min(max(fy, b), b + h)
            ET.SubElement(
                parent,
                f"{{{SVG}}}path",
                {
                    "d": f"M{fx},{fy} L{tx},{ty}",
                    "stroke": "#6C7F87",
                    "stroke-width": "1",
                    "fill": "none",
                    "opacity": ".65",
                },
            )
        node = ET.SubElement(
            parent,
            f"{{{SVG}}}text",
            {
                "x": str(a),
                "y": str(b + size),
                "font-size": str(size),
                "data-label-box": json.dumps([a, b, w, h]),
                **{key.replace("_", "-"): str(v) for key, v in attrs.items()},
            },
        )
        node.text = value
        return node


def teaching_brackets(
    row: ET.Element, teaching: dict[str, Any], locations: list[dict[str, Any]]
) -> None:
    points = {}
    for base in row.iter():
        if base.get("data-base-index") is None:
            continue
        x, y, w, h = base_box(base)
        points[
            base.attrib["data-state-id"],
            base.attrib["data-strand-id"],
            int(base.attrib["data-base-index"]),
        ] = (x + w / 2, y + h / 2)
    parameters = {p["key"]: p for p in teaching["parameters"]}
    canvas = TeachingCanvas(teaching)
    label_bottoms = [
        box[1] + box[3]
        for e in row.iter()
        if e.get("data-label-box")
        for box in [json.loads(e.attrib["data-label-box"])]
    ]
    baseline = max(max(p[1] for p in points.values()) + 66, max(label_bottoms, default=0) + 24)
    lanes: list[list[tuple[float, float]]] = []
    for location in locations:
        key = location["key"]
        parameter = parameters.get(key)
        if parameter is None:
            continue
        definition = parameter["definition"]
        if key != definition["canonical_key"] or definition["representation"] not in (
            "span",
            "threshold",
        ):
            continue
        # Teach the product measurements and the association threshold first.
        # Construction details remain address-linked through the existing overlay.
        if definition["design_role"] != "product" and key != "adapter_annealing_min_nt":
            continue
        anchor = next(
            (
                a
                for a in location["boundary_anchors"]
                if boundary_point(a["start"], points) is not None
                and boundary_point(a["end"], points) is not None
            ),
            None,
        )
        if anchor is None:
            continue
        interface = (
            next(
                (e for e in row.iter() if e.get("data-interface") == key.removesuffix("_gap")),
                None,
            )
            if key in ("left_gap", "right_gap")
            else None
        )
        if interface is not None:
            # The native drawing already locates this gap above the released strand.
            # Reuse it instead of adding a second bracket and label below the molecule.
            interface.set("data-teaching-keys", json.dumps([key]))
            interface.set("data-teaching-bracket", key)
            interface.set("data-boundary-anchor", json.dumps(anchor))
            continue
        start, end = boundary_point(anchor["start"], points), boundary_point(anchor["end"], points)
        assert start is not None and end is not None
        title = definition["label"] + ": " + canvas.label(key)
        left = min(start[0], end[0])
        right = max(max(start[0], end[0]), left + len(title) * 18 * 0.64)
        lane = next(
            (
                i
                for i, spans in enumerate(lanes)
                if all(right + 18 < a or left > z + 18 for a, z in spans)
            ),
            len(lanes),
        )
        if lane == len(lanes):
            lanes.append([])
        lanes[lane].append((left, right))
        y = baseline + lane * 54
        group = ET.SubElement(
            row,
            f"{{{SVG}}}g",
            {
                "data-teaching-keys": json.dumps([key]),
                "data-parameter-keys": json.dumps([key]),
                "data-teaching-bracket": key,
                "data-boundary-anchor": json.dumps(anchor),
                "data-threshold": str(definition["representation"] == "threshold").lower(),
            },
        )
        ET.SubElement(group, f"{{{SVG}}}title").text = title
        for x, z in (start, end):
            ET.SubElement(
                group,
                f"{{{SVG}}}path",
                d=f"M {x} {z + 12} V {y}",
                stroke="#b6c2c6",
                fill="none",
                attrib={"stroke-dasharray": "2 3"},
            )
        ET.SubElement(
            group,
            f"{{{SVG}}}path",
            d=f"M {start[0]} {y - 6} v 6 H {end[0]} v -6",
            stroke="#40535B",
            fill="none",
            attrib={
                "stroke-dasharray": "3 2" if definition["representation"] == "threshold" else "none"
            },
        )
        ET.SubElement(
            group,
            f"{{{SVG}}}text",
            x=str(min(start[0], end[0])),
            y=str(y + 23),
            attrib={"font-size": "18", "data-measurement-label": key},
        ).text = title
