"""Discarded fragment references, kept separate from the retained molecular state."""

from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.atlas import MolecularAtlas
from hop_design.models.construction.projections.inspection import MolecularStateInspection

from ..inspection_layout import inspection_points
from ..primitives.ribbon import ribbon_path
from ..primitives.style import BASE_SIZE
from ..primitives.typography import fitted_base_size
from .placement import origin_points

SVG = "{http://www.w3.org/2000/svg}"


def append_discarded_ghosts(
    root: ET.Element, atlas: MolecularAtlas, retained: MolecularStateInspection
) -> None:
    """Draw recorded discarded strands only when the retained frame agrees exactly.

    These noninteractive reference glyphs have their own address attributes. They
    never acquire active molecular occurrences, contacts, operations or termini.
    """
    if retained.state.phase.value != "selected_fragments":
        return
    precursor = next((s for s in atlas.states if s.state.phase.value == "cleaved_duplex"), None)
    if precursor is None:
        return
    before = inspection_points(precursor)
    origins = origin_points(precursor, before)
    if origins is None:
        return
    actual = {}
    for element in root.iter():
        if element.get("data-base-index") is None:
            continue
        rect = next(e for e in element if e.tag == SVG + "rect")
        text = next(e for e in element if e.tag == SVG + "text")
        actual[element.get("data-strand-id"), int(element.attrib["data-base-index"])] = (
            float(rect.attrib["x"]) + float(rect.attrib["width"]) / 2,
            float(text.attrib["y"]) - 5,
        )
    offsets = []
    retained_origins = set()
    for base in retained.bases:
        key = (base.origin.origin_id, base.origin.origin_strand, base.origin.origin_index)
        if key not in origins:
            return
        retained_origins.add(key)
        x, y = actual[base.address.strand_id, base.address.index]
        a, b = origins[key]
        offsets.append((x - a, y - b))
    dx, dy = offsets[0]
    if any(abs(x - dx) > 1e-6 or abs(y - dy) > 1e-6 for x, y in offsets):
        return
    origin_by_address = {
        (base.address.strand_id, base.address.index): (
            base.origin.origin_id,
            base.origin.origin_strand,
            base.origin.origin_index,
        )
        for base in precursor.bases
    }
    layer = ET.Element(
        SVG + "g",
        {
            "data-discarded-fragment-ghosts": "true",
            "data-reference-state-id": precursor.state.state_id,
            "pointer-events": "none",
            "aria-hidden": "true",
        },
    )
    ET.SubElement(
        layer, SVG + "title"
    ).text = "Discarded fragments from the recorded cleaved precursor; reference only"
    for strand in precursor.state.molecules:
        indices = range(len(strand.sequence))
        if any(origin_by_address[strand.strand_id, i] in retained_origins for i in indices):
            continue
        positions = [
            (before[strand.strand_id, i][0] + dx, before[strand.strand_id, i][1] + dy)
            for i in indices
        ]
        group = ET.SubElement(layer, SVG + "g", {"data-ghost-strand": strand.strand_id})
        ET.SubElement(
            group,
            SVG + "path",
            {
                "data-ghost-ribbon": "true",
                "d": ribbon_path(positions, 13, terminal_extension=6),
                "fill": "white",
                "stroke": "#8C989F",
                "stroke-width": "2.5",
                "stroke-dasharray": "5 4",
                "stroke-linejoin": "round",
            },
        )
        for index, (symbol, (x, y)) in enumerate(zip(strand.sequence, positions, strict=True)):
            glyph = ET.SubElement(
                group,
                SVG + "g",
                {
                    "data-ghost-base-index": str(index),
                    "data-reference-state-id": precursor.state.state_id,
                    "data-reference-strand-id": strand.strand_id,
                },
            )
            ET.SubElement(
                glyph,
                SVG + "text",
                {
                    "x": str(x),
                    "y": str(y + 5),
                    "text-anchor": "middle",
                    "font-size": f"{fitted_base_size(symbol, BASE_SIZE):g}",
                    "fill": "#9CA7AD",
                },
            ).text = symbol
    if len(layer) > 1:
        # Reference fragments lie beneath active region fills and nucleotide ink.
        first = next(i for i, child in enumerate(root) if child.tag == SVG + "g")
        root.insert(first, layer)
