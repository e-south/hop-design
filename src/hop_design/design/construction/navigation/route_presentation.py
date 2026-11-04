"""Compose recorded scenes without changing the selected molecular authority."""

import json
import re
from copy import deepcopy
from typing import cast
from xml.etree import ElementTree as ET

from pydantic import ValidationError

from hop_design.export.construction.molecular.assembly.composition import (
    RoutePresentation,
    assembly_scenes,
)
from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from hop_design.export.construction.molecular.atlas_blocks import route_blocks
from hop_design.export.construction.molecular.primitives.style import FONT_FAMILY
from hop_design.models.construction.complete.state import ConstructionStatePhase
from hop_design.models.construction.projections.atlas import AtlasComparison, MolecularAtlas
from hop_design.serialization import canonical_json_bytes

from ..packets.atlas import MolecularAtlasPacket
from .preview import preview_record
from .types import ChoiceSource, Record


def validate_scene_request(phases: tuple[str, ...], presentation: str, render_policy: str) -> None:
    if (
        not isinstance(phases, (tuple, list))
        or not 1 <= len(phases) <= len(ConstructionStatePhase)
        or any(not isinstance(p, str) for p in phases)
        or len(set(phases)) != len(phases)
        or not set(phases) <= {p.value for p in ConstructionStatePhase}
    ):
        raise ValueError("Request distinct recorded scene phases from one preparation.")
    if presentation not in {"complete", "assembly"} or render_policy not in {"captured", "current"}:
        raise ValueError("Unknown scene presentation or render policy.")


def scene_previews(
    choices: ChoiceSource,
    identity: str,
    answer: Record,
    *,
    phases: tuple[str, ...],
    presentation: str = "complete",
    render_policy: str = "captured",
) -> tuple[dict[str, bytes], Record]:
    """Resolve this viewport's unique phases and draw their exact scenes together.

    Phase continuity is not nucleotide correspondence. Captured artwork retains
    its original composition; current scenes use the complete route's context.
    The finite recorded phase vocabulary bounds one batch to one preparation.
    """
    validate_scene_request(phases, presentation, render_policy)
    presentation = cast(RoutePresentation, presentation)
    from ..editions.reader import AtlasEdition

    atlas: MolecularAtlas | None
    if isinstance(choices, AtlasEdition) and choices._store.compact:
        from ..editions.compact_projection import compact_molecular_projection

        if not any(p["materialized_realization_id"] == identity for p in answer["paths"]):
            raise ValueError("Preview must name a preparation in the recorded pool.")
        # The projection is already a validated model. Keep it typed rather than
        # serializing every state and reconstructing it to draw the visible scenes.
        atlas, summary = compact_molecular_projection(choices, identity, answer)
        captured = False
    else:
        summary, captured = preview_record(choices, identity, answer)
        try:
            atlas = MolecularAtlas.model_validate_json(canonical_json_bytes(summary["atlas"]))
        except ValidationError:
            if not captured:
                raise
            atlas = None
    captured_root = None
    if atlas is not None and captured and render_policy == "captured":
        assert isinstance(choices, AtlasEdition)
        captured_root = ET.fromstring(
            choices._store.read(choices._prefix(identity) + "/atlas/projection.svg")
        )
    return projected_scene_previews(
        atlas,
        identity,
        answer,
        summary,
        phases=phases,
        presentation=presentation,
        captured_root=captured_root,
        rendering="captured" if captured and render_policy == "captured" else "current",
    )


def projected_scene_previews(
    atlas: MolecularAtlas | None,
    identity: str,
    answer: Record,
    summary: Record,
    *,
    phases: tuple[str, ...],
    presentation: RoutePresentation,
    captured_root: ET.Element | None = None,
    rendering: str = "current",
) -> tuple[dict[str, bytes], Record]:
    """Draw requested scenes from the authority already admitted in this request."""
    result: Record = {
        "materialized_realization_id": identity,
        "snapshot_digest": answer["snapshot_digest"],
        "presentation": {"requested": presentation, "effective": presentation},
        "rendering": rendering,
        "roster": [],
        "scenes": [],
        "unavailable": [],
    }
    if atlas is None:
        result.update(
            rendering="captured",
            unavailable=list(phases),
            notice="This recorded schema does not support individual scene inspection.",
        )
        return {}, result
    ids = []
    for phase in phases:
        matches = [s.state.state_id for s in atlas.states if s.state.phase.value == phase]
        if len(matches) == 1:
            ids.append(matches[0])
        else:
            result["unavailable"].append(phase)
    effective: RoutePresentation = presentation
    if captured_root is not None:
        root = captured_root
        archived = root.get("data-atlas-presentation", "complete")
        if archived not in {"complete", "assembly"}:
            raise ValueError("Unknown captured scene presentation.")
        effective = cast(RoutePresentation, archived)
        rows = [e for e in root.iter() if e.get("data-atlas-state") in ids]
    else:
        shown = {
            atlas.states[s.record_index].state.state_id for s in assembly_scenes(atlas, effective)
        }
        if not set(ids) <= shown:
            effective = "complete"
        rows = [
            b.element
            for b in route_blocks(
                atlas,
                None,
                summary["parameter_locations"],
                presentation=effective,
                state_ids=tuple(ids),
            )
        ]
    result["presentation"]["effective"] = effective
    for order, scene in enumerate(assembly_scenes(atlas, effective)):
        state = atlas.states[scene.record_index].state
        result["roster"].append(
            {
                "state_id": state.state_id,
                "phase": state.phase.value,
                "order": order,
                "transition_ids": [
                    atlas.transitions[i].authority_id for i in scene.transition_indices
                ],
            }
        )
    drawings = {}
    for row in rows:
        state_id = row.get("data-atlas-state")
        assert state_id is not None
        frame = f"0 0 {row.attrib['data-atlas-width']} {row.attrib['data-atlas-height']}"
        wrapper = _scene_document(row, frame, identity, captured_root)
        if wrapper is None:
            result["notice"] = "This captured layout supports the full figure, not isolated scenes."
            continue
        drawings[state_id] = ET.tostring(wrapper)
        entry = next(r for r in result["roster"] if r["state_id"] == state_id)
        result["scenes"].append({**entry, "frame": frame})
    found = {s["phase"] for s in result["scenes"]}
    result["unavailable"] = [p for p in phases if p not in found]
    return drawings, result


def _scene_document(
    row: ET.Element, frame: str, identity: str, captured: ET.Element | None
) -> ET.Element | None:
    """Keep captured presentation ancestry and definitions, not just base geometry."""
    wrapper = ET.Element(
        "{http://www.w3.org/2000/svg}svg",
        {
            **(
                captured.attrib
                if captured is not None
                else {"font-family": FONT_FAMILY, "fill": "#243740"}
            ),
            "viewBox": frame,
            "data-preparation-id": identity,
            "data-route-scene": row.attrib["data-atlas-state"],
            "role": "img",
            "aria-label": row.get("data-atlas-phase", "Molecular scene"),
        },
    )
    for attribute in ("width", "height"):
        wrapper.attrib.pop(attribute, None)
    target = wrapper
    if captured is not None:
        parents = {child: parent for parent in captured.iter() for child in parent}
        ancestors = []
        parent = parents[row]
        while parent is not captured:
            ancestors.append(parent)
            parent = parents[parent]
        if not _captured_coordinates_supported(captured, ancestors, row):
            return None
        dependencies: set[ET.Element] = set()
        for element in captured.iter():
            if element not in dependencies and element.tag.endswith(("}defs", "}style")):
                wrapper.append(deepcopy(element))
                dependencies.update(element.iter())
        for ancestor in reversed(ancestors):
            target = ET.SubElement(target, ancestor.tag, ancestor.attrib)
    row = deepcopy(row)
    row.attrib.update({"data-atlas-x": "0", "data-atlas-y": "0", "transform": "translate(0 0)"})
    target.append(row)
    return wrapper


def _captured_coordinates_supported(
    root: ET.Element, ancestors: list[ET.Element], row: ET.Element
) -> bool:
    """Isolate only the producer's untranslated parent frame and translated row."""
    if any(e.tag != "{http://www.w3.org/2000/svg}g" for e in ancestors):
        return False
    if any(e.get("transform") for e in (root, *ancestors)):
        return False
    transform = row.get("transform", "")
    if transform and not re.fullmatch(
        r"translate\(\s*[-+.0-9eE]+[\s,]+[-+.0-9eE]+\s*\)", transform
    ):
        return False
    styles = [e.get("style", "") for e in (root, *ancestors, row)]
    styles.extend(e.text or "" for e in root.iter() if e.tag.endswith("}style"))
    return not any(re.search(r"\b(transform|translate|rotate|scale)\s*:", s, re.I) for s in styles)


def present_route(
    packet: MolecularAtlasPacket, presentation: str, stage: str
) -> MolecularAtlasPacket:
    if presentation == "complete":
        return packet
    summary = json.loads(packet.json_bytes)
    atlas = MolecularAtlas.model_validate_json(canonical_json_bytes(summary["atlas"]))
    visible = {
        atlas.states[s.record_index].state.state_id for s in assembly_scenes(atlas, "assembly")
    }
    # An explicitly inspected cleanup state remains available in the full record.
    if stage != "all" and stage not in visible:
        return packet
    comparison = (
        AtlasComparison.model_validate_json(canonical_json_bytes(summary["comparison"]))
        if summary.get("comparison") is not None
        else None
    )
    files = dict(packet._files)
    files["projection.svg"] = render_molecular_atlas(
        atlas,
        presentation="assembly",
        comparison=comparison,
        parameter_locations=summary["parameter_locations"],
    )
    result = type(packet)._create(files, summary, packet.report_text)
    object.__setattr__(result, "_roots", packet._roots)
    return result


def route_facts(packet: MolecularAtlasPacket, requested: str) -> dict[str, object]:
    root = ET.fromstring(packet.svg_bytes)
    shown = sum(e.get("data-atlas-state") is not None for e in root.iter())
    return {
        "requested": requested,
        "effective": root.get("data-atlas-presentation", "complete"),
        "displayed_states": shown,
        "recorded_states": len(json.loads(packet.json_bytes)["atlas"]["states"]),
    }
