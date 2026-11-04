"""Stage recorded external materials beside their verified destination geometry."""

from hop_design.models.construction.projections.atlas import AtlasMaterialInput, MolecularScenes
from hop_design.models.construction.projections.inspection import MolecularStateInspection

from ..inspection_layout import inspection_points
from ..primitives.materials import PlacedInput
from ..primitives.primer_geometry import outward_side, position_primer
from ..primitives.style import ADAPTER_APPROACH
from .placement import Points, origin_points


def incoming_materials(
    atlas: MolecularScenes, state: MolecularStateInspection, frames: dict[str, Points]
) -> tuple[PlacedInput, ...]:
    points = frames.get(state.state.state_id)
    if points is None:
        points = inspection_points(state)
    result = []
    for item in atlas.inputs:
        if item.pre_state_id != state.state.state_id:
            continue
        if item.material_use.role.value == "ligation_adapter":
            target = next(s for s in atlas.states if s.state.state_id == item.post_state_id)
            target_points = frames.get(target.state.state_id)
            origins = origin_points(target, target_points) if target_points else None
            keys = [
                (item.material_use.use_id, "primary", i)
                for i in range(len(item.material.sequence_5prime))
            ]
            if origins is None or not all(key in origins for key in keys):
                continue
            positions = tuple((origins[key][0], origins[key][1] + ADAPTER_APPROACH) for key in keys)
            result.append(PlacedInput(item, positions))
        elif item.binding is not None and item.binding_state_id != state.state.state_id:
            bound = incoming_primer_template(state, points, item)
            if not bound:
                continue
            center = (
                sum(x for x, _ in points.values()) / len(points),
                sum(y for _, y in points.values()) / len(points),
            )
            side = outward_side(bound, center)
            result.append(
                PlacedInput(
                    item,
                    tuple(
                        position_primer(
                            bound,
                            list(points.values()),
                            outward=side,
                            leading=len(item.material.sequence_5prime) - len(bound),
                        )
                    ),
                    "after copying",
                    side,
                )
            )
    return tuple(result)


def incoming_primer_template(
    state: MolecularStateInspection,
    points: Points,
    item: AtlasMaterialInput,
) -> list[tuple[float, float]]:
    """Locate a future template on recorded ancestry without asserting binding."""
    return [
        points[address.strand_id, address.index]
        for address in item.introduction_reference
        if address.state_id == state.state.state_id
    ]
