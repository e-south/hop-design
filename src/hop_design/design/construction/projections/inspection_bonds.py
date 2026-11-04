"""Locate recorded joining bonds through exact precursor ancestry, never alignment."""

from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.projections.inspection_annotations import InspectionBoundary

from .inspection_annotations import boundary
from .inspection_layout import lineage_key


def inspection_bonds(
    state: ConstructionState, states: tuple[ConstructionState, ...]
) -> tuple[InspectionBoundary, ...]:
    strands = {m.strand_id: m for s in states for m in s.molecules}
    current = {m.strand_id: m for m in state.molecules}
    result = []
    for formed in state.formed_bonds:
        upstream = strands[formed.bond.upstream_strand_id]
        downstream = strands[formed.bond.downstream_strand_id]
        product = current[formed.product_strand_id]
        left = lineage_key(upstream.lineage[-1])
        right = lineage_key(downstream.lineage[0])
        offsets = [
            i
            for i in range(1, len(product.lineage))
            if lineage_key(product.lineage[i - 1]) == left
            and lineage_key(product.lineage[i]) == right
        ]
        if len(offsets) != 1:
            raise ValueError("A recorded joining bond needs unique adjacent precursor ancestry.")
        result.append(boundary(state, product.strand_id, offsets[0]))
    return tuple(result)
