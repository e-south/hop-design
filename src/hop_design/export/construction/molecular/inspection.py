"""Render one recorded state and attach its authoritative molecular addresses."""

import json
from html import escape
from typing import Any, Literal, cast
from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.atlas import AtlasMaterialInput
from hop_design.models.construction.projections.folded_sequence import FoldedSequenceView
from hop_design.models.construction.projections.inspection import MolecularStateInspection

from ..labels import state_label
from .folded_sequence import CHANGES
from .inspection_layout import inspection_points
from .inspection_overlays import inspection_overlays
from .inspection_scene import edge, region_spans
from .parameter_boundaries import mark_parameter_locations
from .primitives.materials import PlacedInput
from .primitives.strands import strand_primitives
from .primitives.style import FONT_FAMILY, INK, TITLE_SIZE

SVG = "{http://www.w3.org/2000/svg}"
INKSCAPE = "{http://www.inkscape.org/namespaces/inkscape}"


def _annotate_inspection_element(
    root: ET.Element,
    projection: MolecularStateInspection,
    material_inputs: tuple[AtlasMaterialInput, ...] = (),
    *,
    site_labels: Literal["all", "operations"] = "all",
    label_site_ids: frozenset[str] | None = None,
    staged_inputs: tuple[PlacedInput, ...] = (),
) -> ET.Element:
    """Mutate only this new drawing; preserve the authoritative projection."""
    bases = {(b.strand_index, b.address.index): b for b in projection.bases}
    positions = {}
    for element in root.iter(SVG + "g"):
        if "data-base-index" not in element.attrib:
            continue
        key = (int(element.get("data-strand", "0")), int(element.attrib["data-base-index"]))
        base = bases[key]
        element.attrib.update(
            {
                "data-state-id": base.address.state_id,
                "data-strand-id": base.address.strand_id,
                "data-region": base.region or "unmapped",
                "data-neighborhood": base.neighborhood or "",
                "data-focus-relation": base.focus_relation or "",
                "tabindex": "0",
                "role": "button",
                "aria-label": f"{base.base}, {base.neighborhood or 'unmapped region'}, "
                f"position {base.address.index + 1}",
            }
        )
        for child in element:
            if child.tag == SVG + "text":
                child.set("fill", INK)
            if base.focus_relation is not None and child.tag == SVG + "rect":
                child.set("stroke", "#8A4FA1")
                child.set("stroke-width", "2")
        rect = next(element.iter(SVG + "rect"))
        text = next(element.iter(SVG + "text"))
        positions[base.address.strand_id, base.address.index] = (
            float(rect.attrib["x"]) + float(rect.attrib["width"]) / 2,
            float(text.attrib["y"]) - 5,
        )
    overlay = ET.fromstring(
        inspection_overlays(
            projection,
            positions,
            material_inputs,
            site_labels=site_labels,
            label_site_ids=label_site_ids,
            staged_inputs=staged_inputs,
        )
    )
    regions = ET.fromstring(
        '<g xmlns="http://www.w3.org/2000/svg" data-regions="true">'
        + region_spans(projection, positions)
        + "</g>"
    )
    # Behind the glyphs, after the background; no imported/cloned document trees.
    first = next(i for i, child in enumerate(root) if child.tag == SVG + "g")
    root.insert(first, regions)
    root.insert(first + 1, overlay)
    for group in root.iter(SVG + "g"):
        label = ""
        if "data-strand-primitive" in group.attrib:
            label = "Strand: " + group.attrib["data-strand-primitive"]
        elif "data-site-id" in group.attrib or "data-primer-binding" in group.attrib:
            title = next(group.iter(SVG + "title"), None)
            if title is not None:
                label = (title.text or "").split(";")[0]
        elif "data-cut" in group.attrib:
            label = "Cut: " + group.attrib["data-cut"] + " " + group.get("data-boundary", "")
        if label:
            group.set(INKSCAPE + "label", label)
    for element in root.iter():
        for attribute in ("data-from", "data-to"):
            if attribute in element.attrib:
                element.set(
                    attribute,
                    json.dumps(
                        [projection.state.state_id, *json.loads(element.attrib[attribute])],
                        separators=(",", ":"),
                    ),
                )
        for attribute in ("data-members", "data-path-members"):
            if attribute in element.attrib:
                element.set(
                    attribute,
                    json.dumps(
                        [
                            [projection.state.state_id, *address]
                            for address in json.loads(element.attrib[attribute])
                        ]
                    ),
                )
    frame = list(map(float, root.attrib["viewBox"].split()))
    for element in root.iter(SVG + "text"):
        if "data-label-box" in element.attrib:
            x, y, w, h = json.loads(element.attrib["data-label-box"])
            frame[2] = max(frame[2], x + w + 28)
            frame[3] = max(frame[3], y + h + 55)
    root.set("viewBox", " ".join(map(str, frame)))
    for element in root.iter(SVG + "text"):
        if "data-caption" in element.attrib:
            element.set("y", str(frame[3] - 24))
    return root


def _points(projection: MolecularStateInspection) -> dict[tuple[str, int], tuple[float, float]]:
    return inspection_points(projection)


def render_molecular_inspection(
    projection: MolecularStateInspection,
    *,
    comparison: FoldedSequenceView | None = None,
    comparison_stage: str | None = None,
    material_inputs: tuple[AtlasMaterialInput, ...] = (),
    parameter_locations: list[dict[str, Any]] | None = None,
    site_labels: Literal["all", "operations"] = "all",
    label_site_ids: frozenset[str] | None = None,
    staged_inputs: tuple[PlacedInput, ...] = (),
    layout_points: dict[tuple[str, int], tuple[float, float]] | None = None,
) -> bytes:
    """Serialize one scene at the export boundary."""
    root = molecular_inspection_element(
        projection,
        comparison=comparison,
        comparison_stage=comparison_stage,
        material_inputs=material_inputs,
        parameter_locations=parameter_locations,
        site_labels=site_labels,
        label_site_ids=label_site_ids,
        staged_inputs=staged_inputs,
        layout_points=layout_points,
    )
    return cast(bytes, ET.tostring(root, encoding="utf-8"))


def molecular_inspection_element(
    projection: MolecularStateInspection,
    *,
    comparison: FoldedSequenceView | None = None,
    comparison_stage: str | None = None,
    material_inputs: tuple[AtlasMaterialInput, ...] = (),
    parameter_locations: list[dict[str, Any]] | None = None,
    site_labels: Literal["all", "operations"] = "all",
    label_site_ids: frozenset[str] | None = None,
    staged_inputs: tuple[PlacedInput, ...] = (),
    layout_points: dict[tuple[str, int], tuple[float, float]] | None = None,
) -> ET.Element:
    state = projection.state
    points = layout_points if layout_points is not None else _points(projection)
    width = max(1000, max(x for x, _ in points.values()) + 90)
    height = max(y for _, y in points.values()) + 110
    changes = {}
    notices = []
    if comparison is not None:
        regions = (
            comparison.regions
            if comparison_stage == "hairpin"
            else comparison.endpoint_sequence_differences
        )
        for strand_index, region in enumerate(regions):
            change_strand = 0 if comparison_stage == "hairpin" else strand_index
            offset = region.observed_span[0] if comparison_stage == "hairpin" else 0
            for column in region.columns:
                if column.observed_offset is not None and column.kind in CHANGES:
                    changes[change_strand, offset + column.observed_offset] = column.kind
            if region.correspondence in ("ambiguous_minimum_edit", "unresolved_budget"):
                words = (
                    f"{region.reference_sequence} → {region.observed_sequence}; "
                    if max(len(region.reference_sequence), len(region.observed_sequence)) <= 16
                    else ""
                )
                notices.append(
                    f"{region.region}: {words}positional correspondence unresolved; "
                    "see exact record"
                )
    height += 20 * len(notices)
    center = (min(x for x, _ in points.values()) + max(x for x, _ in points.values())) / 2
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<g font-family="{FONT_FAMILY}">',
        f'<text data-stage-title="true" x="{center}" y="{TITLE_SIZE}" '
        f'text-anchor="middle" font-size="{TITLE_SIZE}">{escape(state_label(state.phase))}</text>',
    ]
    for pair in state.pairings:
        lines.append(
            edge(
                "pair",
                (pair.left_strand_id, pair.left_index),
                (pair.right_strand_id, pair.right_index),
                points,
                pair_kind=pair.kind.value,
            )
        )
    lines.append(strand_primitives(projection, points, changes, CHANGES))
    for i, notice in enumerate(notices):
        lines.append(
            f'<text data-correspondence-notice="true" x="28" '
            f'y="{height - 66 - 20 * i}" font-size="13">{escape(notice)}</text>'
        )
    if changes:
        lines.append(
            f'<text data-change-legend="true" x="28" y="{height - 46}" font-size="13">'
            "Purple: verified substitution · Green: added position.</text>"
        )
    lines.append(
        f'<text data-caption="true" x="28" y="{height - 24}" font-size="14">'
        "Unmarked termini: OH; P: phosphate.</text></g></svg>"
    )
    root = _annotate_inspection_element(
        ET.fromstring("\n".join(lines)),
        projection,
        material_inputs,
        site_labels=site_labels,
        label_site_ids=label_site_ids,
        staged_inputs=staged_inputs,
    )
    if parameter_locations is not None:
        mark_parameter_locations(root, parameter_locations, projection)
    return root
