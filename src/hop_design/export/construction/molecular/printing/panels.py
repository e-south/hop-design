"""Split native scenes between glyphs; retain each nucleotide occurrence exactly once."""

import json
from copy import deepcopy
from dataclasses import dataclass
from textwrap import wrap
from typing import Any
from xml.etree import ElementTree as ET

from ..label_layout import LabelPlacer

SVG = "http://www.w3.org/2000/svg"


@dataclass(frozen=True)
class ScenePanel:
    element: ET.Element
    height: float
    description: dict[str, Any]


def base_box(base: ET.Element) -> tuple[float, float, float, float]:
    rect = next((e for e in base if e.tag.endswith("}rect")), None)
    if rect is not None:
        return tuple(float(rect.get(k, "0")) for k in ("x", "y", "width", "height"))  # type: ignore[return-value]
    text = next((e for e in base if e.tag.endswith("}text")), base)
    return float(text.get("x", "0")), float(text.get("y", "16")) - 16, 14, 20


def _windows(
    boxes: list[tuple[float, float, float, float]], width: float
) -> list[tuple[float, float]]:
    merged: list[list[float]] = []
    for x, _, w, _ in sorted(boxes):
        if merged and x <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], x + w)
        else:
            merged.append([x, x + w])
    if any(b - a > width for a, b in merged):
        raise ValueError("No publication-width split can preserve these overlapping base glyphs.")
    lo, end = min(0.0, merged[0][0]), merged[-1][1]
    result = []
    while end - lo > width:
        ideal = lo + width
        cut = ideal
        for a, b in merged:
            if a < ideal < b:
                cut = a - 1
                break
        if cut <= lo:
            raise ValueError("Scene splitting cannot advance without clipping a nucleotide.")
        result.append((lo, cut))
        lo = cut
    result.append((lo, max(lo + 1, end + 12)))
    return [(a, b) for a, b in result if any(a <= x + w / 2 < b for x, _, w, _ in boxes)]


def _spans(bases: list[ET.Element]) -> list[dict[str, Any]]:
    strands: dict[str, list[int]] = {}
    for base in bases:
        strands.setdefault(base.get("data-strand-id", ""), []).append(
            int(base.attrib["data-base-index"])
        )
    rows = []
    for strand, indices in strands.items():
        start = previous = sorted(indices)[0]
        for value in sorted(indices)[1:]:
            if value != previous + 1:
                rows.append({"strand_id": strand, "start": start, "stop": previous + 1})
                start = value
            previous = value
        rows.append({"strand_id": strand, "start": start, "stop": previous + 1})
    return rows


def scene_panels(row: ET.Element, width: float) -> tuple[ScenePanel, ...]:
    """Native-coordinate clips with unique bases and reflowed labels, never new molecules.

    The short labels can move within their panel. Exact geometry, cuts, recognition
    footprints and contacts retain native coordinates. Continuation metadata names
    the coordinate windows and original base ranges; a view break is not cleavage.
    """
    bases = [e for e in row.iter() if e.get("data-base-index") is not None]
    if not bases:
        raise ValueError("A molecular scene needs addressed nucleotide glyphs.")
    windows = _windows([base_box(b) for b in bases], width - 24)
    title = next(
        (e.text for e in row.iter() if e.get("data-stage-title")), row.get("data-atlas-state")
    )
    return tuple(
        _panel(row, bases, windows, ordinal, width, title) for ordinal in range(1, len(windows) + 1)
    )


def _panel(
    row: ET.Element,
    bases: list[ET.Element],
    windows: list[tuple[float, float]],
    ordinal: int,
    width: float,
    title: str | None,
) -> ScenePanel:
    lo, hi = windows[ordinal - 1]
    owned = [b for b in bases if lo <= base_box(b)[0] + base_box(b)[2] / 2 < hi]
    occupied = [base_box(b) for b in owned]
    placer = LabelPlacer(occupied, horizontal_bounds=(lo + 12, lo + width - 24))
    label_bottom = 0.0
    labels: list[ET.Element] = []

    def project(element: ET.Element) -> ET.Element | None:
        nonlocal label_bottom
        if element.get("data-annotation-block"):
            annotation_lines = [e for e in element if e.tag.endswith("}text") and e.text]
            if not annotation_lines:
                return None
            x, y = float(annotation_lines[0].attrib["x"]), float(annotation_lines[0].attrib["y"])
            owner = next((i for i, (_, z) in enumerate(windows) if x < z), len(windows) - 1)
            if owner != ordinal - 1:
                return None
            block = ET.fromstring(
                placer.block(
                    x,
                    y,
                    [
                        (
                            e.get("data-label-kind", "annotation"),
                            e.text or "",
                            e.get("fill", "#182B34"),
                            int(float(e.get("font-size", "32"))),
                        )
                        for e in annotation_lines
                    ],
                )
            )
            for new, old in zip(block, annotation_lines, strict=True):
                if old.get("data-primer-chemistry"):
                    new.set("data-primer-chemistry", "true")
            _, top, _, height = map(float, block.attrib["data-drawing-box"].split())
            label_bottom = max(label_bottom, top + height)
            labels.append(block)
            return None
        if element.get("data-base-index") is not None:
            x, _, w, _ = base_box(element)
            return deepcopy(element) if lo <= x + w / 2 < hi else None
        if element.get("data-input-base-index") is not None:
            x = float(element.attrib["x"]) + 5
            return deepcopy(element) if lo <= x < hi else None
        if any(
            element.get(k)
            for k in (
                "data-stage-title",
                "data-operation",
                "data-operation-arrow",
                "data-operation-arrowhead",
                "data-atlas-input",
                "data-caption",
            )
        ):
            return None
        if element.tag.endswith("}text"):
            if not element.text:
                return None
            x, y = float(element.get("x", "0")), float(element.get("y", "0"))
            # Names at the far right remain on the last scene panel.
            panel = min(
                len(windows) - 1,
                next((i for i, (_, z) in enumerate(windows) if x < z), len(windows) - 1),
            )
            if panel != ordinal - 1:
                return None
            size = max(18.0, float(element.get("font-size", "18")))
            lines = wrap(element.text, width=max(1, int((width - 48) / (size * 0.64))))
            text_width = max(map(len, lines)) * size * 0.64
            x = max(lo + 12, min(x, lo + width - text_width - 24))
            a, b, w, h = placer.place(x, y, max(lines, key=len), size=int(size))
            h += (len(lines) - 1) * (size + 5)
            placer.occupied.append((a, b, w, h))
            label_bottom = max(label_bottom, b + h)
            clone = deepcopy(element)
            clone.attrib.update(
                {
                    "x": str(a),
                    "y": str(b + size),
                    "text-anchor": "start",
                    "font-size": str(size),
                    "data-label-box": json.dumps([a, b, w, h]),
                }
            )
            clone.text = None
            for child in list(clone):
                clone.remove(child)
            for i, line in enumerate(lines):
                ET.SubElement(
                    clone, f"{{{SVG}}}tspan", x=str(a), y=str(b + size + i * (size + 5))
                ).text = line
            labels.append(clone)
            return None
        clone = ET.Element(element.tag, element.attrib)
        if clone.get("data-scene-content"):
            # Page panels measure and reflow in native molecular coordinates.
            clone.attrib.pop("transform", None)
            clone.attrib.pop("data-scene-y", None)
        if clone.get("id"):
            clone.set("id", f"{clone.attrib['id']}-panel-{ordinal}")
        clone.text = element.text
        for child in element:
            copied = project(child)
            if copied is not None:
                clone.append(copied)
        return clone

    drawing = project(row)
    assert drawing is not None
    drawing.attrib.pop("transform", None)
    drawing.attrib.pop("data-atlas-state", None)
    drawing.attrib.pop("data-atlas-order", None)
    bottom = max(max(y + h for _, y, _, h in occupied), label_bottom) + 22
    panel = ET.Element(
        f"{{{SVG}}}g",
        {"data-scene-panel": str(ordinal), "data-scene-state": row.attrib["data-atlas-state"]},
    )
    if ordinal == 1:
        panel.set("data-atlas-state", row.attrib["data-atlas-state"])
    heading = ET.SubElement(
        panel,
        f"{{{SVG}}}text",
        x=str(width / 2),
        y="24",
        attrib={"font-size": "24", "text-anchor": "middle", "data-stage-title": "true"},
    )
    suffix = f" · {ordinal}/{len(windows)}" if len(windows) > 1 else ""
    heading.text = (title or "Molecular state") + suffix
    # Explicit transforms/clips work in both SVG browsers and the vector PDF encoder.
    clip_id = f"scene-{row.get('data-atlas-order', '0')}-{ordinal}"
    definitions = ET.SubElement(panel, f"{{{SVG}}}defs")
    clip = ET.SubElement(definitions, f"{{{SVG}}}clipPath", id=clip_id)
    ET.SubElement(clip, f"{{{SVG}}}rect", x=str(lo), y="0", width=str(hi - lo), height=str(bottom))
    viewport = ET.SubElement(
        panel,
        f"{{{SVG}}}g",
        {
            "transform": f"translate({12 - lo} 40)",
            "clip-path": f"url(#{clip_id})",
        },
    )
    viewport.append(drawing)
    annotation_layer = ET.SubElement(panel, f"{{{SVG}}}g", transform=f"translate({12 - lo} 40)")
    annotation_layer.extend(labels)
    height = bottom + 46
    if len(windows) > 1:
        ET.SubElement(
            panel,
            f"{{{SVG}}}text",
            x="12",
            y=str(height + 18),
            attrib={"font-size": "18", "data-view-continuation": "true"},
        ).text = (
            "Continue →  View split; strands and contacts continue."
            if ordinal < len(windows)
            else "← continued  View split; no additional cleavage."
        )
        height += 44
    return ScenePanel(
        panel,
        height,
        {
            "state_id": row.attrib["data-atlas-state"],
            "part": ordinal,
            "parts": len(windows),
            "x_range": [lo, hi],
            "base_spans": _spans(owned),
        },
    )
