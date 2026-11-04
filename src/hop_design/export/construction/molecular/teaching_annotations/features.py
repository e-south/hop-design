"""Local dimensions on the selected hairpin, using recorded boundary projections."""

import json
from typing import Any
from xml.etree import ElementTree as ET

from ..parameter_boundaries import boundary_point
from .layout import OverviewLabels

SVG = "http://www.w3.org/2000/svg"


def local_dimensions(
    root: ET.Element,
    state_id: str,
    points: dict[tuple[str, int], tuple[float, float]],
    teaching: dict[str, Any],
    locations: list[dict[str, Any]],
    labels: OverviewLabels,
) -> None:
    parameters = {p["key"]: p for p in teaching["parameters"]}
    qualified = {(state_id, strand, i): p for (strand, i), p in points.items()}
    middle = (min(y for _, y in points.values()) + max(y for _, y in points.values())) / 2
    basal = next(
        (e for e in root.iter() if e.get("data-parameter-anchor") == "open_side_paired_positions"),
        None,
    )
    basal_box = json.loads(basal.attrib["data-anchor-box"]) if basal is not None else None
    names = {
        "foldback_arm_bp": "Extension A =",
        "join_offset_nt": "Join D =",
        "basal_nick_offset_nt": "Nick gap n =",
        "open_side_paired_positions": "Paired",
        "adapter_annealing_min_nt": "Anneal ≥",
        "left_gap": "Left gap",
        "right_gap": "Right gap",
    }
    for location in locations:
        key = location["key"]
        parameter = parameters.get(key)
        if key not in names or parameter is None or parameter["value"] is None:
            continue
        projected = [
            (boundary_point(a["start"], qualified), boundary_point(a["end"], qualified))
            for a in location.get("boundary_occurrences", location["boundary_anchors"])
        ]
        pair = next(((a, b) for a, b in projected if a is not None and b is not None), None)
        if pair is None:
            continue
        a, b = pair
        outside = -1 if (a[1] + b[1]) / 2 <= middle else 1
        y = (min(a[1], b[1]) - 24) if outside < 0 else (max(a[1], b[1]) + 24)
        group = ET.SubElement(
            root,
            f"{{{SVG}}}g",
            {
                "data-teaching-bracket": key,
                "data-teaching-keys": json.dumps([key]),
            },
        )
        ET.SubElement(
            group,
            f"{{{SVG}}}path",
            {
                "d": f"M{a[0]},{a[1] + outside * 12} V{y} H{b[0]} V{b[1] + outside * 12}",
                "stroke": "#526A75",
                "fill": "none",
                "stroke-width": "1.5",
                "stroke-dasharray": "3 3"
                if key in {"left_gap", "right_gap", "adapter_annealing_min_nt"}
                else "none",
            },
        )
        unit = parameter["definition"]["unit"]
        label = f"{names[key]} {parameter['value']} {unit}"
        x, baseline, align = (
            (a[0] + b[0]) / 2,
            y - 10 if outside < 0 else y + labels.size + 8,
            "middle",
        )
        if (
            key
            in {"open_side_paired_positions", "adapter_annealing_min_nt", "basal_nick_offset_nt"}
            and basal_box
        ):
            x = basal_box[0] + basal_box[2] + 24
            baseline = basal_box[1] + basal_box[3] + labels.size + 22
            align = "start"
        labels.text(
            group,
            x,
            baseline,
            label,
            text_anchor=align,
            feature_anchor=((a[0] + b[0]) / 2, y),
        )
        ET.SubElement(group, f"{{{SVG}}}title").text = parameter["definition"]["measurement"]
    arm = parameters.get("foldback_arm_bp", {}).get("value")
    join = parameters.get("join_offset_nt", {}).get("value")
    if arm is not None and join is not None:
        anchor = next(
            (e for e in root.iter() if e.get("data-parameter-anchor") == "foldback_arm_bp"), None
        )
        if anchor is not None:
            x, y, w, h = json.loads(anchor.attrib["data-anchor-box"])
            labels.text(
                anchor,
                x + w / 2,
                y + h + 70,
                f"R = A \u2212 D = {arm - join} bp",
                text_anchor="middle",
            )


def projected_end_spans(root: ET.Element, labels: OverviewLabels) -> None:
    """Mark future end contributors without inventing exposed ends on a hairpin."""
    for anchor in list(root.iter()):
        key = anchor.get("data-parameter-anchor")
        if key not in {"left_end_word", "right_end_word"}:
            continue
        x, y, w, h = json.loads(anchor.attrib["data-anchor-box"])
        ET.SubElement(
            anchor,
            f"{{{SVG}}}rect",
            {
                "x": str(x),
                "y": str(y),
                "width": str(w),
                "height": str(h),
                "rx": "3",
                "fill": "none",
                "stroke": "#95582C",
                "stroke-width": "2",
                "stroke-dasharray": "4 3",
                "data-projected-end": key.removesuffix("_end_word"),
            },
        )
