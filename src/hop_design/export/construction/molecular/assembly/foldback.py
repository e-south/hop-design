"""A schematic closing cue anchored to the recorded next ligation junction."""

from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.atlas import MolecularAtlas
from hop_design.models.construction.projections.inspection import MolecularStateInspection

from .placement import Points, origin_points


def foldback_cue(atlas: MolecularAtlas, state: MolecularStateInspection, points: Points) -> str:
    if state.state.phase.value != "annealed_complex":
        return ""
    closed = next(
        (s for s in atlas.states if s.state.phase.value == "foldback_closed_hairpin"), None
    )
    origins = origin_points(state, points)
    if closed is None or origins is None or len(closed.formed_bond_boundaries) != 1:
        return ""
    join = closed.formed_bond_boundaries[0]
    addresses = {b.address: b for b in closed.bases}
    endpoints = []
    for address in (join.before, join.after):
        if address not in addresses:
            return ""
        base = addresses[address]
        key = (base.origin.origin_id, base.origin.origin_strand, base.origin.origin_index)
        if key not in origins:
            return ""
        endpoints.append(origins[key])
    x = max(p[0] for p in points.values()) + 24
    y = min(p[1] for p in endpoints) - 18
    return (
        f'<g data-foldback-cue="true" data-drawing-box="{x - 6} {y - 58} 90 90">'
        "<title>Foldback direction at the closing junction; schematic cue</title>"
        f'<path d="M{x + 10},{y + 20} C{x + 100},{y + 20} {x + 80},{y - 64} {x},{y - 32}" '
        'fill="none" stroke="#356B27" stroke-width="5" stroke-linecap="round"/>'
        f'<path d="M{x - 3},{y - 30} L{x + 24},{y - 29} L{x + 12},{y - 50} Z" fill="#356B27"/></g>'
    )


def append_cue(root: ET.Element, cue: str) -> None:
    if cue:
        root.append(ET.fromstring('<g xmlns="http://www.w3.org/2000/svg">' + cue + "</g>"))
