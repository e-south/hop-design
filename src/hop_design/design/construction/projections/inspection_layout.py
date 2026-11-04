"""Choose recorded drawing correspondence without importing prior associations."""

from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.molecular_state import MaterialBaseLineage

type Origin = tuple[str, str, int]


def lineage_key(base: MaterialBaseLineage) -> Origin:
    return base.origin_id, base.origin_strand.value, base.origin_index


def _signature(
    state: ConstructionState,
) -> tuple[frozenset[Origin], frozenset[frozenset[Origin]]] | None:
    addresses = {
        (m.strand_id, b.product_index): lineage_key(b) for m in state.molecules for b in m.lineage
    }
    atoms = frozenset(addresses.values())
    if len(atoms) != len(addresses):
        return None  # Duplicated provenance cannot establish unique drawing correspondence.
    pairs = frozenset(
        frozenset(
            (addresses[p.left_strand_id, p.left_index], addresses[p.right_strand_id, p.right_index])
        )
        for p in state.pairings
    )
    return atoms, pairs


def inspection_layout_frame(
    state: ConstructionState, states: tuple[ConstructionState, ...]
) -> ConstructionState | None:
    signature = _signature(state)
    if signature is None:
        return None
    if state.phase.value in {"denatured_fragments", "selected_fragments"}:
        # A prior paired state supplies positions, never contacts. Only unique
        # retained origins qualify; no sequence alignment or invented ancestry.
        position = next((i for i, s in enumerate(states) if s.state_id == state.state_id), 0)
        for index in range(position - 1, -1, -1):
            prior = states[index]
            candidate = _signature(prior)
            if prior.pairings and candidate and signature[0] <= candidate[0]:
                return inspection_layout_frame(prior, states[:index]) or prior
        return None
    if not state.pairings:
        return None
    # Joining/nicking changes covalent components, not these recorded contacts.
    # Only geometry uses the frame; the displayed state owns all bonds and pairs.
    candidates = [
        s for s in states if len(s.molecules) < len(state.molecules) and _signature(s) == signature
    ]
    return min(candidates, key=lambda s: (len(s.molecules), s.state_id)) if candidates else None
