"""Draw explicit coincident boundaries and requirement thresholds on exact scene geometry."""

import json
from typing import Any
from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.inspection import MolecularStateInspection


def mark_parameter_locations(
    root: ET.Element, locations: list[dict[str, Any]], inspection: MolecularStateInspection
) -> None:
    """Attach one measurement vocabulary to bases, persistent footprints and active cuts."""
    parameters: dict[tuple[str, str, int], list[str]] = {}
    for location in locations:
        for address in location["occurrences"]:
            key = (address["state_id"], address["strand_id"], address["index"])
            parameters.setdefault(key, []).append(location["key"])
    roles = {o.operation_id: o.role for o in inspection.operations}
    for element in root.iter():
        attrs = element.attrib
        keys = []
        if "data-base-index" in attrs:
            keys = parameters.get(
                (attrs["data-state-id"], attrs["data-strand-id"], int(attrs["data-base-index"])), []
            )
        role = attrs.get("data-site-role") or roles.get(attrs.get("data-operation-id", ""))
        if role in ("basal_nick", "foldback_nick"):
            prefix = role.removesuffix("_nick")
            keys = [f"{prefix}_method", f"{prefix}_strand"]
        elif role == "end_generation":
            keys = ["release_method"]
        if keys:
            attrs["data-parameter-keys"] = json.dumps(keys)
    add_parameter_boundaries(root, locations)


def add_parameter_boundaries(root: ET.Element, locations: list[dict[str, Any]]) -> None:
    points = {}
    for el in root.iter():
        if "data-base-index" not in el.attrib:
            continue
        rect = next(c for c in el if c.tag.endswith("}rect"))
        a = el.attrib
        points[(a["data-state-id"], a["data-strand-id"], int(a["data-base-index"]))] = (
            float(rect.attrib["x"]) + float(rect.attrib["width"]) / 2,
            float(rect.attrib["y"]) + float(rect.attrib["height"]) / 2,
        )

    for location in locations:
        threshold = location["definition"]["representation"] == "threshold"
        if not location["zero_extent"] and not threshold:
            continue
        for anchor in location["boundary_anchors"]:
            start, end = (
                boundary_point(anchor["start"], points),
                boundary_point(anchor["end"], points),
            )
            if start is None or end is None:
                continue
            x, y = start
            x2, y2 = end
            group = ET.SubElement(
                root,
                "g",
                {
                    "data-parameter-boundary": location["key"],
                    "data-parameter-keys": json.dumps([location["key"]]),
                    "data-threshold": str(threshold).lower(),
                },
            )
            ET.SubElement(group, "title").text = location["definition"]["label"] + (
                ": required footprint" if threshold else ": coincident boundaries (0)"
            )
            ET.SubElement(
                group,
                "path",
                {
                    "d": f"M {x} {y + 10} v 6 L {x2} {y2 + 16} v -6",
                    "fill": "none",
                    "stroke": "#986D36" if threshold else "#40535B",
                    "stroke-width": "1.5",
                    "stroke-dasharray": "3 2" if threshold else "none",
                },
            )


def boundary_point(
    boundary: dict[str, Any], points: dict[tuple[str, str, int], tuple[float, float]]
) -> tuple[float, float] | None:
    neighbors = [
        points.get((a["state_id"], a["strand_id"], a["index"]))
        for a in (boundary["before"], boundary["after"])
        if a is not None
    ]
    if not neighbors or any(p is None for p in neighbors):
        return None
    known = [p for p in neighbors if p is not None]
    if len(known) == 1:
        edge = boundary["after"] or boundary["before"]
        step = 1 if boundary["after"] is not None else -1
        x, y = known[0]
        neighbor = points.get((edge["state_id"], edge["strand_id"], edge["index"] + step))
        if neighbor is not None:
            return x - (neighbor[0] - x) / 2, y - (neighbor[1] - y) / 2
        return x - step * 8, y
    return sum(p[0] for p in known) / len(known), sum(p[1] for p in known) / len(known)
