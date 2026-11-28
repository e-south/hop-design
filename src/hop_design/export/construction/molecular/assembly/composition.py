"""Select drawing scenes without pruning or rewriting molecular authority."""

from dataclasses import dataclass
from typing import Literal

from hop_design.models.construction.projections.atlas import MolecularAtlas

RoutePresentation = Literal["complete", "assembly"]


@dataclass(frozen=True)
class Scene:
    record_index: int
    transition_indices: tuple[int, ...]
    title: str | None = None
    operation: str | None = None


def assembly_scenes(atlas: MolecularAtlas, presentation: RoutePresentation) -> tuple[Scene, ...]:
    if presentation not in ("complete", "assembly"):
        raise ValueError(f"Unknown route presentation: {presentation}")
    phases = tuple(state.state.phase.value for state in atlas.states)
    cleanup = ("cleaved_duplex", "denatured_fragments", "selected_fragments", "annealed_complex")
    start = (
        next((i for i in range(len(phases) - 3) if phases[i : i + 4] == cleanup), None)
        if presentation == "assembly"
        else None
    )
    scenes = []
    for index in range(len(phases)):
        if start is not None and index in (start, start + 1):
            continue
        if start is not None and index == start - 1:
            scenes.append(
                Scene(
                    index, tuple(range(index, start + 2)), operation="Cleave, separate and retain"
                )
            )
        elif start is not None and index == start + 2:
            scenes.append(
                Scene(
                    index, (index,), title="Cleaved and retained", operation="Fold back and anneal"
                )
            )
        else:
            scenes.append(
                Scene(
                    index,
                    (index,) if index < len(atlas.transitions) else (),
                    title="Folded and annealed"
                    if start is not None and index == start + 3
                    else None,
                    operation="Hairpin PCR"
                    if phases[index] == "adapter_ligated"
                    and index + 1 < len(phases)
                    and phases[index + 1] == "hairpin_pcr_duplex"
                    else None,
                )
            )
    return tuple(scenes)
