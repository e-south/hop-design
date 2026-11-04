"""Measure exact state scenes before route placement."""

from dataclasses import dataclass
from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.atlas import MolecularAtlas

from .assembly.composition import RoutePresentation
from .assembly.foldback import append_cue, foldback_cue
from .assembly.inputs import incoming_materials
from .assembly.placement import assembly_points
from .inspection import molecular_inspection_element
from .primitives.annotation_policy import RouteSiteLabels, named_sites
from .primitives.extent import scene_extent


@dataclass(frozen=True)
class MeasuredScenes:
    scenes: dict[int, tuple[ET.Element, float, float, float]]
    staged_ids: frozenset[str]


def atlas_scenes(
    atlas: MolecularAtlas,
    *,
    site_labels: RouteSiteLabels = "narrative",
    presentation: RoutePresentation = "complete",
    record_indices: tuple[int, ...] | None = None,
) -> MeasuredScenes:
    scenes = {}
    frames = assembly_points(atlas)
    staged = {
        state.state.state_id: incoming_materials(atlas, state, frames) for state in atlas.states
    }
    staged_ids = frozenset(
        item.item.material_use.use_id for inputs in staged.values() for item in inputs
    )
    introduced: set[str] = set()
    for index, state in enumerate(atlas.states):
        labels = named_sites(state, site_labels, introduced)
        introduced.update(s.enzyme_name for s in state.recognition_sites if s.recognition)
        if record_indices is not None and index not in record_indices:
            continue
        root = molecular_inspection_element(
            state,
            layout_points=frames.get(state.state.state_id),
            staged_inputs=staged[state.state.state_id],
            label_site_ids=labels,
            material_inputs=tuple(
                item
                for item in atlas.inputs
                if item.binding_state_id == state.state.state_id
                and item.material_use.use_id not in staged_ids
            ),
        )
        if state.state.state_id in frames:
            append_cue(root, foldback_cue(atlas, state, frames[state.state.state_id]))
        width, height = scene_extent(root)
        positions = []
        for element in root.iter():
            if element.attrib.get("data-neighborhood") == "stem":
                rect = next(e for e in element if e.tag.endswith("}rect"))
                positions.append(float(rect.attrib["x"]))
        anchor = min(positions) if positions else 0
        scenes[index] = root, width, height, anchor
    return MeasuredScenes(
        scenes,
        staged_ids,
    )
