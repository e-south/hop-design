"""Build ordered molecular scenes with their recorded inputs and next operation."""

import json
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.atlas import AtlasComparison, MolecularAtlas

from ..labels import atlas_state_label, operation_label
from .assembly.composition import RoutePresentation, assembly_scenes
from .atlas_layout import atlas_scenes
from .atlas_placement import BlockExtent
from .parameter_boundaries import mark_parameter_locations
from .primitives.annotation_policy import RouteSiteLabels
from .primitives.extent import scene_extent
from .primitives.inputs import draw_inputs
from .primitives.operations import draw_operation
from .primitives.scene_header import attach_scene_header
from .primitives.style import ANNOTATION_SIZE, TITLE_SIZE, base_ink, object_id

SVG = "http://www.w3.org/2000/svg"


@dataclass(frozen=True)
class RouteBlock:
    element: ET.Element
    extent: BlockExtent


def route_blocks(
    atlas: MolecularAtlas,
    comparison: AtlasComparison | None,
    locations: list[dict[str, Any]],
    *,
    site_labels: RouteSiteLabels = "narrative",
    presentation: RoutePresentation = "complete",
    state_ids: tuple[str, ...] | None = None,
) -> tuple[RouteBlock, ...]:
    roster = assembly_scenes(atlas, presentation)
    if state_ids is not None:
        visible = {atlas.states[s.record_index].state.state_id for s in roster}
        if len(set(state_ids)) != len(state_ids) or not set(state_ids) <= visible:
            raise ValueError("Requested scene is absent, repeated, or hidden in this presentation.")
    selected = tuple(
        (index, scene)
        for index, scene in enumerate(roster)
        if state_ids is None or atlas.states[scene.record_index].state.state_id in state_ids
    )
    substitutions = (
        {
            (b.address.state_id, b.address.strand_id, b.address.index)
            for b in comparison.substitutions
        }
        if comparison
        else set()
    )
    additions = (
        {(a.state_id, a.strand_id, a.index) for a in comparison.additions} if comparison else set()
    )
    unresolved = (
        {(a.state_id, a.strand_id, a.index) for a in comparison.unresolved_positions}
        if comparison
        else set()
    )
    # Only suppress a list when the full input has a recorded binding glyph in
    # this route. Derived/unrecorded template inputs retain their explicit list.
    binding_inputs = {
        item.material_use.use_id: item
        for item in atlas.inputs
        if item.binding is not None
        and item.binding_context == "recorded_state"
        and any(state.state.state_id == item.binding_state_id for state in atlas.states)
    }
    blocks = []
    measured = atlas_scenes(
        atlas,
        site_labels=site_labels,
        presentation=presentation,
        record_indices=tuple(scene.record_index for _, scene in selected),
    )
    for index, scene in selected:
        state = atlas.states[scene.record_index]
        root, width, height, anchor = measured.scenes[scene.record_index]
        name = scene.title or atlas_state_label(state.state.phase.value)
        root.tag = f"{{{SVG}}}g"
        root.attrib = {
            "id": object_id("stage", state.state.state_id),
            "{http://www.inkscape.org/namespaces/inkscape}label": name,
            "data-atlas-state": state.state.state_id,
            "data-atlas-phase": state.state.phase.value,
            "data-atlas-order": str(index),
            "data-atlas-anchor": str(anchor),
        }
        for child in list(root):
            if child.tag.endswith("}rect"):
                root.remove(child)
        centers = []
        for element in root.iter():
            attrs = element.attrib
            if attrs.get("data-caption"):
                element.text = ""
            if "data-base-index" not in attrs:
                continue
            attrs["data-preparation-id"] = atlas.materialized_realization_id
            address = (
                attrs["data-state-id"],
                attrs["data-strand-id"],
                int(attrs["data-base-index"]),
            )
            attrs["data-occurrence"] = json.dumps(
                [atlas.materialized_realization_id, *address], separators=(",", ":")
            )
            rect = next(e for e in element if e.tag.endswith("}rect"))
            centers.append(float(rect.attrib["x"]) + float(rect.attrib["width"]) / 2)
            if address in substitutions or address in additions:
                attrs["data-change"] = "substitution" if address in substitutions else "added"
                rect.set("fill", "#DED2EC" if address in substitutions else "#D2EAD7")
                next(e for e in element if e.tag.endswith("}text")).set(
                    "fill", base_ink(attrs.get("data-neighborhood", ""), rect.get("fill"))
                )
            if address in unresolved:
                attrs["data-correspondence"] = "unresolved"
                rect.set("stroke", "#986A26")
                rect.set("stroke-dasharray", "3 2")
        if comparison:
            for glyph in root.iter():
                item = binding_inputs.get(glyph.get("data-primer-binding", ""))
                if item and item.material_use.role.value in comparison.material_roles:
                    glyph.set("data-material-changed", "true")
                    title_node = next(e for e in glyph if e.tag.endswith("}title"))
                    title_node.text = (title_node.text or "").replace(
                        ";", " · changed versus reference;", 1
                    )
        mark_parameter_locations(root, locations, state)
        center = (min(centers) + max(centers)) / 2
        title = next(e for e in root.iter() if e.get("data-stage-title") == "true")
        title.text = name
        title.set("font-size", str(TITLE_SIZE))
        title.set("font-weight", "600")
        attach_scene_header(root)
        width, height = scene_extent(root)
        if scene.transition_indices:
            transition = atlas.transitions[scene.transition_indices[0]]
            root.set(
                "data-transition-ids",
                json.dumps([atlas.transitions[i].authority_id for i in scene.transition_indices]),
            )
            width, height = draw_operation(
                root,
                center,
                height,
                width,
                transition.kind,
                scene.operation or operation_label(transition.kind),
            )
            inputs = tuple(
                item
                for item in atlas.inputs
                if item.pre_state_id == state.state.state_id
                and item.material_use.use_id not in binding_inputs
                and item.material_use.use_id not in measured.staged_ids
            )
            if inputs:
                width, height = draw_inputs(
                    root, inputs, width, height + ANNOTATION_SIZE + 16, comparison
                )
        root.set("data-atlas-width", str(width))
        root.set("data-atlas-height", str(height))
        blocks.append(RouteBlock(root, BlockExtent(width, height, anchor, state.state.phase.value)))
    return tuple(blocks)
