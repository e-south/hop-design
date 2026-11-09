"""Presentation-only coordinates; current states retain covalent and pairing authority."""

import math

from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.projections.inspection import MolecularStateInspection
from hop_design.models.molecular_state import MaterialBaseLineage

from .primitives.style import SCENE_TOP


def _state_points(state: ConstructionState) -> dict[tuple[str, int], tuple[float, float]]:
    """Lay out strands using their recorded contacts."""
    points: dict[tuple[str, int], tuple[float, float]] = {}
    cursor = float(SCENE_TOP)
    for strand in sorted(
        state.molecules,
        key=lambda m: (
            -len(m.sequence),
            m.lineage[0].origin_strand.value != "primary",
            m.strand_id,
        ),
    ):
        self_pairs = [
            sorted((p.left_index, p.right_index))
            for p in state.pairings
            if p.left_strand_id == p.right_strand_id == strand.strand_id
        ]
        if self_pairs and len({a + b for a, b in self_pairs}) == 1:
            turn_left = max(a for a, _ in self_pairs) + 1
            turn_right = min(b for _, b in self_pairs)
            pair_sum = self_pairs[0][0] + self_pairs[0][1]
            point: tuple[float, float]
            for i in range(len(strand.sequence)):
                if i < turn_left:
                    point = (100 + i * 16, cursor)
                elif i >= turn_right:
                    point = (100 + (pair_sum - i) * 16, cursor + 44)
                else:
                    angle = -math.pi / 2 + math.pi * (i - turn_left + 1) / (
                        turn_right - turn_left + 1
                    )
                    point = (
                        100 + (turn_left - 1) * 16 + 28 * math.cos(angle),
                        cursor + 22 + 22 * math.sin(angle),
                    )
                points[strand.strand_id, i] = point
            cursor += 120
            continue
        contacts = []
        for pair in state.pairings:
            if pair.left_strand_id == strand.strand_id:
                i, partner = pair.left_index, (pair.right_strand_id, pair.right_index)
            elif pair.right_strand_id == strand.strand_id:
                i, partner = pair.right_index, (pair.left_strand_id, pair.left_index)
            else:
                continue
            if partner in points:
                contacts.append((i, points[partner]))
        direction, offset, y = 1, 100.0, cursor
        if len(contacts) > 1:
            contacts.sort()
            first, last = contacts[0], contacts[-1]
            direction = 1 if last[1][0] > first[1][0] else -1
            offset = first[1][0] - direction * first[0] * 16
            y = first[1][1] + 44
        for i in range(len(strand.sequence)):
            points[strand.strand_id, i] = (offset + direction * i * 16, y)
        cursor = max(cursor + 80, y + 80)
    minimum = min(x for x, _ in points.values())
    return {key: (x - minimum + 100, y) for key, (x, y) in points.items()}


def inspection_points(
    projection: MolecularStateInspection,
) -> dict[tuple[str, int], tuple[float, float]]:
    frame = projection.layout_frame
    if frame is None:
        return _fan_handles(projection.state, _state_points(projection.state))
    points = _state_points(frame)

    def key(base: MaterialBaseLineage) -> tuple[str, str, int]:
        return base.origin_id, base.origin_strand, base.origin_index

    by_origin = {
        key(b): points[m.strand_id, b.product_index] for m in frame.molecules for b in m.lineage
    }
    mapped = {
        (m.strand_id, b.product_index): by_origin[key(b)]
        for m in projection.state.molecules
        for b in m.lineage
    }
    if projection.state.phase.value in {"denatured_fragments", "selected_fragments"}:
        center = (min(y for _, y in points.values()) + max(y for _, y in points.values())) / 2
        # Retain the precursor's x registration and orientation. A small outward
        # translation shows dissociation while the current state supplies bonds.
        return {
            address: (x, y + (-16 if y <= center else 16)) for address, (x, y) in mapped.items()
        }
    return _fan_handles(projection.state, mapped)


def _fan_handles(
    state: ConstructionState, points: dict[tuple[str, int], tuple[float, float]]
) -> dict[tuple[str, int], tuple[float, float]]:
    """Unpaired handles depart at 45 degrees, then run parallel to the stem.

    Five base spacings set the drawing's bend, not a molecular requirement.
    Short tails stop before that bend; all backbone steps keep their length.
    """
    if state.phase.value not in {"foldback_closed_hairpin", "adapter_annealed", "adapter_ligated"}:
        return points
    paired = {
        (strand, index)
        for pair in state.pairings
        for strand, index in (
            (pair.left_strand_id, pair.left_index),
            (pair.right_strand_id, pair.right_index),
        )
    }
    if not paired:
        return points
    center = sum(points[p][1] for p in paired) / len(paired)
    result = dict(points)
    for strand in state.molecules:
        indices = [i for s, i in paired if s == strand.strand_id]
        if not indices:
            continue
        first, last = min(indices), max(indices)
        for indices_out, anchor, neighbor in (
            (range(first), first, first - 1),
            (range(last + 1, len(strand.sequence)), last, last + 1),
        ):
            if not indices_out:
                continue
            x, y = points[strand.strand_id, anchor]
            direction = -1 if points[strand.strand_id, neighbor][0] < x else 1
            vertical = -1 if y <= center else 1
            for i in indices_out:
                count = abs(i - anchor)
                diagonal = min(count, 5) * 16 / math.sqrt(2)
                parallel = max(0, count - 5) * 16
                result[strand.strand_id, i] = (
                    x + direction * (diagonal + parallel),
                    y + vertical * diagonal,
                )
    dx = max(0, 100 - min(x for x, _ in result.values()))
    dy = max(0, SCENE_TOP - min(y for _, y in result.values()))
    return {key: (x + dx, y + dy) for key, (x, y) in result.items()}
