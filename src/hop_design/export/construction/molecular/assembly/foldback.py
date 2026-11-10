"""A schematic fold cue anchored to recorded future self-pairing, before folding."""

from math import hypot
from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.atlas import MolecularAtlas
from hop_design.models.construction.projections.inspection import MolecularStateInspection

from ..primitives.style import OPERATION_STROKE, REGION_COLORS
from .placement import Points, origin_points


def foldback_cue(atlas: MolecularAtlas, state: MolecularStateInspection, points: Points) -> str:
    if state.state.phase.value != "selected_fragments":
        return ""
    folded = next((s for s in atlas.states if s.state.phase.value == "annealed_complex"), None)
    origins = origin_points(state, points)
    if folded is None or origins is None:
        return ""
    addresses = {(b.address.strand_id, b.address.index): b for b in folded.bases}
    molecules = {m.strand_id: m for m in folded.state.molecules}
    endpoints = None
    for pair in folded.state.pairings:
        if pair.left_strand_id != pair.right_strand_id:
            continue
        strand = molecules[pair.left_strand_id]
        ends = (0, len(strand.sequence) - 1)
        terminal = next((i for i in ends if i in (pair.left_index, pair.right_index)), None)
        if terminal is None:
            continue
        partner = pair.right_index if pair.left_index == terminal else pair.left_index
        mapped = []
        for index in (terminal, partner):
            base = addresses[strand.strand_id, index]
            key = (base.origin.origin_id, base.origin.origin_strand, base.origin.origin_index)
            if key not in origins:
                break
            mapped.append(origins[key])
        if len(mapped) == 2:
            endpoints = mapped
            break
    if endpoints is None:
        return ""
    (x, y), (target, target_y) = endpoints
    direction = 1 if target > x else -1
    start, end = x - direction * 24, target - direction * 16
    peak = min(y, target_y) - 84
    end_y = target_y - 18
    dx, dy = direction * 80, end_y - peak
    length = hypot(dx, dy)
    ux, uy = dx / length, dy / length
    base_x, base_y = end - ux * 26, end_y - uy * 26
    color = REGION_COLORS["closing"]
    left, right = min(start, end) - 18, max(start, end) + 66
    return (
        f'<g data-foldback-cue="true" data-cue-phase="before-folding" '
        f'data-drawing-box="{left} {peak - 6} {right - left} {max(y, target_y) - peak + 24}">'
        "<title>Fold the exposed retained end toward its recorded pairing partner; "
        "schematic cue</title>"
        f'<path d="M{start},{y - 8} C{start - direction * 48},{peak} '
        f'{end - direction * 80},{peak} {end},{end_y}" fill="none" '
        f'stroke="{color}" stroke-width="{OPERATION_STROKE}" '
        'stroke-dasharray="14 8" stroke-linecap="round"/>'
        f'<path d="M{end},{end_y} L{base_x - uy * 11},{base_y + ux * 11} '
        f'L{base_x + uy * 11},{base_y - ux * 11} Z" fill="{color}"/></g>'
    )


def append_cue(root: ET.Element, cue: str) -> None:
    if cue:
        root.append(ET.fromstring('<g xmlns="http://www.w3.org/2000/svg">' + cue + "</g>"))
