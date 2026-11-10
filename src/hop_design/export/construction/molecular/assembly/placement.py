"""Hold assembly parts in one drawing frame using unambiguous material ancestry."""

from hop_design.models.construction.projections.atlas import MolecularAtlas
from hop_design.models.construction.projections.inspection import MolecularStateInspection

from ..inspection_layout import inspection_points

Points = dict[tuple[str, int], tuple[float, float]]
ASSEMBLY_PHASES = frozenset(
    {
        "annealed_complex",
        "foldback_closed_hairpin",
        "adapter_annealed",
        "adapter_ligated",
    }
)


def assembly_points(atlas: MolecularAtlas) -> dict[str, Points]:
    """Geometry comes from the joined hairpin; each scene still supplies its own bonds."""
    frame = next((s for s in atlas.states if s.state.phase.value == "adapter_ligated"), None)
    if frame is None:
        return {}
    points = inspection_points(frame)
    origins = origin_points(frame, points)
    if origins is None:
        return {}
    result = {}
    for state in atlas.states:
        if state.state.phase.value not in ASSEMBLY_PHASES:
            continue
        mapped = {}
        seen = set()
        for base in state.bases:
            key = (base.origin.origin_id, base.origin.origin_strand, base.origin.origin_index)
            if key not in origins or key in seen:
                break
            seen.add(key)
            mapped[base.address.strand_id, base.address.index] = origins[key]
        else:
            result[state.state.state_id] = mapped
    linear = next((s for s in atlas.states if s.state.phase.value == "cleaved_duplex"), None)
    retained = next((s for s in atlas.states if s.state.phase.value == "selected_fragments"), None)
    if linear is not None and retained is not None:
        origins = origin_points(linear, inspection_points(linear))
        if origins is not None:
            mapped = {}
            for base in retained.bases:
                key = (base.origin.origin_id, base.origin.origin_strand, base.origin.origin_index)
                if key not in origins:
                    break
                mapped[base.address.strand_id, base.address.index] = origins[key]
            else:
                result[retained.state.state_id] = mapped
    return result


def origin_points(
    state: MolecularStateInspection, points: Points
) -> dict[tuple[str, str, int], tuple[float, float]] | None:
    result: dict[tuple[str, str, int], tuple[float, float]] = {}
    for base in state.bases:
        key = (base.origin.origin_id, base.origin.origin_strand, base.origin.origin_index)
        if key in result:
            return None
        result[key] = points[base.address.strand_id, base.address.index]
    return result
