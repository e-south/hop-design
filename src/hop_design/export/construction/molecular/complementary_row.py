"""Locate an absent recognition row from recorded local contacts and ancestry."""

from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.projections.inspection import MolecularStateInspection

from .inspection_layout import _state_points
from .primitives.style import DUPLEX_ROW_GAP


def complementary_row_offset(
    projection: MolecularStateInspection,
    cluster: list[tuple[str, int]],
    points: dict[tuple[str, int], tuple[float, float]],
) -> float | None:
    """Use the nearest paired address on the same strand, never a global midpoint.

    Dissociated fragments retain their qualified precursor's row registration;
    the frame provides geometry only and introduces no active pairing.
    """

    def offsets(
        state: ConstructionState,
        locations: dict[tuple[str, int], tuple[float, float]],
        addresses: list[tuple[str, int]],
    ) -> list[tuple[int, int]]:
        candidates = []
        for pair in state.pairings:
            a, b = (pair.left_strand_id, pair.left_index), (pair.right_strand_id, pair.right_index)
            for anchor, partner in ((a, b), (b, a)):
                dy = locations[partner][1] - locations[anchor][1]
                if abs(dy) < 1:
                    continue
                for strand, index in addresses:
                    if strand == anchor[0]:
                        candidates.append((abs(index - anchor[1]), 1 if dy > 0 else -1))
        return candidates

    candidates = offsets(projection.state, points, cluster)
    frame = projection.layout_frame
    if not candidates and frame is not None:
        by_origin = {
            (b.origin_id, b.origin_strand, b.origin_index): (m.strand_id, b.product_index)
            for m in frame.molecules
            for b in m.lineage
        }
        mapped = [
            by_origin[(b.origin.origin_id, b.origin.origin_strand, b.origin.origin_index)]
            for b in projection.bases
            if (b.address.strand_id, b.address.index) in cluster
        ]
        candidates = offsets(frame, _state_points(frame), mapped)
    if candidates:
        nearest = min(distance for distance, _ in candidates)
        signs = {sign for distance, sign in candidates if distance == nearest}
        return next(iter(signs)) * DUPLEX_ROW_GAP if len(signs) == 1 else None
    # An unprocessed source strand is the recorded future reference row.
    if not projection.state.pairings and frame is None:
        origins = {
            b.origin.origin_strand.value
            for b in projection.bases
            if (b.address.strand_id, b.address.index) in cluster
        }
        if len(origins) == 1:
            return DUPLEX_ROW_GAP if origins == {"primary"} else -DUPLEX_ROW_GAP
    return None
