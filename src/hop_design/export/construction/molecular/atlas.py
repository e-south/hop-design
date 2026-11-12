"""Compose ordered molecular blocks without coupling chronology to page coordinates."""

from html import escape
from typing import Any, Literal
from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.atlas import AtlasComparison, MolecularAtlas

from .assembly.composition import RoutePresentation
from .atlas_blocks import route_blocks
from .atlas_placement import place_route
from .atlas_reading_order import continuation_svg
from .primitives.annotation_policy import RouteSiteLabels, site_key
from .primitives.style import ANNOTATION_SIZE, FONT_FAMILY, SCENE_CLEARANCE, TITLE_SIZE


def render_molecular_atlas(
    atlas: MolecularAtlas,
    *,
    comparison: AtlasComparison | None = None,
    parameter_locations: list[dict[str, Any]] | None = None,
    site_labels: RouteSiteLabels = "narrative",
    presentation: RoutePresentation = "complete",
) -> bytes:
    blocks = route_blocks(
        atlas,
        comparison,
        parameter_locations or [],
        site_labels=site_labels,
        presentation=presentation,
    )
    placement = place_route(tuple(b.extent for b in blocks))
    rows = []
    continuation_start = None
    continuation_end = None
    from_side = False
    side_origin: Literal["loop-cap", "retained-foldback"] = "loop-cap"
    for index, (block, position) in enumerate(zip(blocks, placement.positions, strict=True)):
        if (
            position.column == "0"
            and index + 1 < len(blocks)
            and placement.positions[index + 1].column == "1"
        ):
            arrow = next(e for e in block.element if e.get("data-operation-arrow"))
            x, y, width, height = map(float, arrow.attrib["data-drawing-box"].split())
            continuation_start = position.x + x + width / 2, position.y + y + height - 22
            if block.extent.phase in {"annealed_complex", "selected_fragments"}:
                scene = next(e for e in block.element if e.get("data-scene-content"))
                cap = [
                    next(e for e in base if e.tag.endswith("}rect"))
                    for base in scene.iter()
                    if base.get("data-base-index") is not None
                    and base.get("data-neighborhood") == "loop"
                ]
                if cap:
                    candidate = (
                        position.x
                        + max(float(r.attrib["x"]) + float(r.attrib["width"]) for r in cap)
                        + 18,
                        position.y
                        + float(scene.attrib["data-scene-y"])
                        + sum(float(r.attrib["y"]) + float(r.attrib["height"]) / 2 for r in cap)
                        / len(cap),
                    )
                    following, target = blocks[index + 1], placement.positions[index + 1]
                    entry_x = target.x + float(following.element.get("data-scene-entry-x", "0"))
                    entry_y = target.y + float(following.element.get("data-scene-entry-y", "100"))
                    if candidate[0] + 24 < entry_x and candidate[1] > entry_y:
                        continuation_start = candidate
                        from_side = True
                        side_origin = (
                            "retained-foldback"
                            if block.extent.phase == "selected_fragments"
                            else "loop-cap"
                        )
                        block.element.remove(arrow)
                        label = next(e for e in block.element if e.get("data-operation"))
                        label.set("x", str(continuation_start[0] - position.x + 24))
                        label.set("y", str(continuation_start[1] - position.y - 28))
                        label.set("data-operation-label-placement", side_origin)
            for element in list(block.element):
                if element.get("data-operation-arrowhead"):
                    block.element.remove(element)
        if position.column == "1" and continuation_end is None:
            continuation_end = (
                position.x + float(block.element.get("data-scene-entry-x", "0")),
                position.y + float(block.element.get("data-scene-entry-y", "100")),
            )
        if (
            index + 1 < len(blocks)
            and block.extent.phase == "adapter_ligated"
            and blocks[index + 1].extent.phase == "hairpin_pcr_duplex"
        ):
            target = placement.positions[index + 1]
            title = next(e for e in blocks[index + 1].element if e.get("data-stage-title"))
            end_x = target.x + float(title.attrib["x"]) - position.x
            end_y = target.y + float(title.attrib["y"]) - TITLE_SIZE - position.y - SCENE_CLEARANCE
            arrow = next(e for e in block.element if e.get("data-operation-arrow"))
            x, y, width, _ = map(float, arrow.attrib["data-drawing-box"].split())
            x += width / 2
            end = end_y - 20
            if end <= y:
                raise ValueError("The hairpin PCR connector requires downward clearance.")
            direction = 1 if end_x > x else -1
            radius = min(32.0, abs(end_x - x) / 2, (end - y) / 4)
            middle = (y + end) / 2
            arrow.set(
                "d",
                f"M{x},{y} V{middle - radius} "
                f"Q{x},{middle} {x + direction * radius},{middle} "
                f"H{end_x - direction * radius} "
                f"Q{end_x},{middle} {end_x},{middle + radius} V{end}",
            )
            arrow.set("data-connector-target-phase", "hairpin_pcr_duplex")
            arrow.set("data-connector-target-x", str(end_x))
            arrow.set("data-connector-corner-radius", str(radius))
            label = next(e for e in block.element if e.get("data-operation"))
            label.set("y", str((y + middle - radius) / 2 + ANNOTATION_SIZE * 0.35))
            arrow.set(
                "data-drawing-box", f"{min(x, end_x) - 14} {y} {abs(x - end_x) + 28} {end_y - y}"
            )
            head = next(e for e in block.element if e.get("data-operation-arrowhead"))
            head.set(
                "d", f"M{end_x - 14},{end_y - 24} L{end_x},{end_y} L{end_x + 14},{end_y - 24} Z"
            )
        block.element.attrib.update(
            {
                "data-atlas-x": str(position.x),
                "data-atlas-y": str(position.y),
                "data-atlas-column": position.column,
                "transform": f"translate({position.x} {position.y})",
            }
        )
        rows.append(ET.tostring(block.element, encoding="unicode"))
    rows.append(
        continuation_svg(
            placement,
            continuation_start,
            continuation_end,
            from_side=from_side,
            side_origin=side_origin,
        )
    )
    y = placement.height + 14
    if presentation == "complete":
        key, y = site_key(atlas, placement.width, y)
        rows.append(key)
        notes_top = y
        y += 18  # The key returns its lower edge; the next text needs an ascent.
        notes = [
            f'<text x="28" y="{y}" font-size="18">'
            "Strands and contacts through the processing route.</text>"
        ]
        y += 28
        if atlas.construction_cost:
            for line in atlas.construction_cost.summary_lines:
                notes.append(
                    f'<text data-construction-cost="true" x="28" y="{y}" font-size="18">'
                    f"{escape(line)}</text>"
                )
                y += 28
        if comparison:
            notes.append(
                f'<text data-change-legend="true" x="28" y="{y}" font-size="18">'
                "Purple: substitution · green: added · dashed amber: "
                "correspondence unresolved.</text>"
            )
            y += 28
            if comparison.notices:
                notes.append(
                    f'<text data-correspondence-notice="true" x="28" y="{y}" font-size="18">'
                    "Some positional correspondence is unresolved; "
                    "see the exact comparison sheet.</text>"
                )
                y += 28
            if "source_ssdna" in comparison.material_roles:
                notes.append(
                    f'<text x="28" y="{y}" font-size="18">'
                    "Source oligo changed versus reference.</text>"
                )
                y += 28
        rows.append(
            f'<g data-atlas-notes="true" data-atlas-y="{notes_top}" '
            f'data-atlas-height="{y + 20 - notes_top}">' + "".join(notes) + "</g>"
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {placement.width} {y + 20}" '
        f'data-atlas="true" data-atlas-presentation="{presentation}" '
        f'data-recorded-state-count="{len(atlas.states)}" '
        'data-atlas-layout="columns-with-finish" role="img" '
        'aria-label="Complete molecular preparation: down the left column, '
        'then the right, then the full-width finish">'
        '<rect width="100%" height="100%" fill="white"/>'
        f'<g font-family="{FONT_FAMILY}" fill="#243740">' + "\n".join(rows) + "</g></svg>"
    ).encode()
