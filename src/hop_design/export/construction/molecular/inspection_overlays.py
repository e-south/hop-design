"""Draw only typed operation and interface annotations projected by the owning layer."""

from html import escape
from typing import Literal

from hop_design.models.construction.projections.atlas import AtlasMaterialInput
from hop_design.models.construction.projections.inspection import MolecularStateInspection
from hop_design.models.construction.projections.inspection_annotations import InspectionBoundary
from hop_design.models.construction.variants.inspection import MolecularAddress

from ..labels import terminal_label
from .label_layout import LabelPlacer
from .material_bindings import material_binding_overlays
from .primitives.annotation_policy import footprint_color
from .primitives.materials import PlacedInput, input_box, staged_materials
from .primitives.style import (
    ANNOTATION_SIZE,
    CUT_HALF_WIDTH,
    CUT_REACH,
    FONT_FAMILY,
    INK,
    TERMINAL_SIZE,
    TITLE_SIZE,
    object_id,
)
from .recognition_sites import recognition_site_overlays


def inspection_overlays(
    projection: MolecularStateInspection,
    points: dict[tuple[str, int], tuple[float, float]],
    material_inputs: tuple[AtlasMaterialInput, ...] = (),
    *,
    site_labels: Literal["all", "operations"] = "all",
    label_site_ids: frozenset[str] | None = None,
    staged_inputs: tuple[PlacedInput, ...] = (),
) -> str:
    rows = [
        '<g xmlns="http://www.w3.org/2000/svg" data-inspection-overlays="true" '
        f'font-family="{FONT_FAMILY}">'
    ]
    labels = LabelPlacer(
        [(x - 10, y - 24, 23, 48) for x, y in points.values()], top=TITLE_SIZE + 18
    )
    labels.occupied.extend(
        input_box(item.positions, primer=item.item.binding is not None, outward=item.outward)
        for item in staged_inputs
    )
    middle = (min(y for _, y in points.values()) + max(y for _, y in points.values())) / 2

    def point(address: MolecularAddress) -> tuple[float, float]:
        return points[address.strand_id, address.index]

    def boundary(value: InspectionBoundary) -> tuple[float, float]:
        if value.before is not None and value.after is not None:
            x, y = point(value.before)
            u, v = point(value.after)
            return (x + u) / 2, (y + v) / 2
        edge = value.after if value.after is not None else value.before
        assert edge is not None
        x, y = point(edge)
        step = 1 if value.after is not None else -1
        neighbor = points.get((edge.strand_id, edge.index + step))
        dx = (neighbor[0] - x) if neighbor is not None else step * 16
        return x - dx / 2, y

    # Reserve cuts before placing names: a leader must never obscure the event.
    for operation in projection.operations:
        for cut in operation.cuts:
            cx, cy = boundary(cut.boundary)
            outside = -1 if cy <= middle else 1
            labels.occupied.append(
                (
                    cx - CUT_HALF_WIDTH - 3,
                    cy - CUT_REACH - 3 if outside < 0 else cy - 3,
                    2 * CUT_HALF_WIDTH + 6,
                    CUT_REACH + 6,
                )
            )
    for join in projection.formed_bond_boundaries:
        jx, jy = boundary(join)
        labels.occupied.append((jx - 16, jy - 38 if jy <= middle else jy - 3, 32, 42))
    for strand in projection.state.molecules:
        for index, chemistry in (
            (0, terminal_label("5\u2032", strand.five_prime_end)),
            (len(strand.sequence) - 1, terminal_label("3\u2032", strand.three_prime_end)),
        ):
            label = chemistry.removesuffix("OH")
            x, y = points[strand.strand_id, index]
            neighbor = 1 if index == 0 else index - 1
            nx, _ = points.get((strand.strand_id, neighbor), (x + 16, y))
            outside_x = x - len(label) * TERMINAL_SIZE * 0.64 - 18 if nx > x else x + 18
            rows.append(
                labels.text("terminus", outside_x, y + 7, label, INK, TERMINAL_SIZE)
                .replace(
                    'data-label-kind="terminus"',
                    f'data-label-kind="terminus" data-terminal-chemistry="{chemistry}" '
                    f'data-terminal-strand="{escape(strand.strand_id)}" '
                    f'data-terminal-index="{index}"',
                )
                .replace(f">{label}</text>", f">{label}<title>{chemistry}</title></text>")
            )
    rows.append(material_binding_overlays(material_inputs, points, labels))
    rows.append(staged_materials(staged_inputs, labels))
    rows.append(
        recognition_site_overlays(
            projection, points, labels, site_labels=site_labels, label_site_ids=label_site_ids
        )
    )

    def text(x: float, y: float, label: str, color: str) -> None:
        rows.append(labels.text("cut-or-dimension", x, y, label, color, ANNOTATION_SIZE))

    for join in projection.formed_bond_boundaries:
        x, y = boundary(join)
        assert join.before is not None and join.after is not None
        outside = -1 if y <= middle else 1
        near, far = y + outside * 19, y + outside * 34
        rows.append(
            f'<g data-formed-bond="{join.after.index}" data-event-glyph="bond-bridge" '
            f'data-bond-strand="{escape(join.after.strand_id)}" '
            f'data-drawing-box="{x - 14} {min(y, far) - 3} 28 40">'
            "<title>Recorded ligation bond</title>"
            f'<path d="M{x},{y} V{far}" stroke="{INK}" stroke-width="1.8"/>'
            f'<path d="M{x - 12},{near} V{far} H{x + 12} V{near}" '
            f'fill="none" stroke="{INK}" stroke-width="3.2" stroke-linejoin="round"/></g>'
        )

    for operation in projection.operations:
        positions = [point(a) for a in operation.recognition]
        x, z = min(p[0] for p in positions) - 8, max(p[0] for p in positions) + 8
        y, w = min(p[1] for p in positions) - 16, max(p[1] for p in positions) + 16
        color = footprint_color(projection, operation.role, operation.recognition)
        rows.append(
            f'<g id="{object_id("operation", projection.state.state_id, operation.operation_id)}" '
            f'data-operation-id="{escape(operation.operation_id)}" '
            f'data-timing="{operation.timing}">'
        )
        if not projection.recognition_sites:
            rows.append(
                f'<rect x="{x}" y="{y}" width="{z - x}" height="{w - y}" rx="5" '
                f'fill="{color}" fill-opacity=".14" stroke="{color}" stroke-opacity=".5" '
                f'data-recognition-start="{operation.recognition_start}" '
                f'data-recognition-end="{operation.recognition_end}"/>'
            )
        direction = (
            point(operation.recognition[min(1, len(operation.recognition) - 1)])[0]
            - point(operation.recognition[0])[0]
        )
        forward = operation.orientation == "forward"
        arrow = "→" if (direction >= 0) == forward else "←"
        if not projection.recognition_sites:
            text(x, y - 10, operation.enzyme_name + " " + arrow, color)
        cuts = []
        for cut in operation.cuts:
            cx, cy = boundary(cut.boundary)
            cuts.append((cx, cy))
            # A triangle points to the literal between-base boundary. A short
            # dashed stem distinguishes a projected cut from a present break.
            outside = -1 if cy <= middle else 1
            cut_id = object_id("cut", projection.state.state_id, operation.operation_id, cut.strand)
            mark_fill = color if operation.timing == "applied" else "white"
            rows.append(
                f'<g id="{cut_id}" '
                f'data-cut="{cut.strand}" data-boundary="{cut.precursor_offset}" '
                f'data-cut-timing="{operation.timing}" '
                f'data-cut-point="{cx} {cy}" '
                f'data-drawing-box="{cx - CUT_HALF_WIDTH - 3} '
                f"{cy - CUT_REACH - 3 if outside < 0 else cy - 3} "
                f'{2 * CUT_HALF_WIDTH + 6} {CUT_REACH + 6}">'
                f'<path d="M{cx - CUT_HALF_WIDTH},{cy + outside * CUT_REACH} '
                f"L{cx},{cy + outside * 10} "
                f'L{cx + CUT_HALF_WIDTH},{cy + outside * CUT_REACH} Z" '
                f'fill="{mark_fill}" stroke="{color}" stroke-width="2.5"/>'
            )
            if operation.timing == "applied":
                rows.append(
                    f'<path data-cut-notch="true" d="M{cx},{cy - 14} V{cy + 14}" '
                    'stroke="white" stroke-width="6"/>'
                )
            dash = ' stroke-dasharray="6 3"' if operation.timing != "applied" else ""
            rows.append(
                f'<path d="M{cx},{cy + outside * 10} L{cx},{cy}" '
                f'stroke="{color}" stroke-width="3.2"{dash}/></g>'
            )
        if len(cuts) == 2:
            (cx, cy), (dx, dy) = cuts
            rows.append(
                f'<path d="M{cx},{cy} V{(cy + dy) / 2} H{dx} V{dy}" fill="none" '
                f'stroke="{color}" stroke-width="3.2" stroke-dasharray="6 3" '
                'data-paired-cut-boundary="true"/>'
            )
        rows.append("</g>")
    for interface in projection.interfaces:
        x, y = boundary(interface.paired_start)
        z, _ = boundary(interface.paired_end)
        by = min(v for _, v in points.values()) - 33
        rows.append(
            f'<g data-interface="{interface.side}" data-gap-bp="{interface.distance_bp}" '
            f'data-end-polarity="{interface.polarity}" data-end-word="{interface.sequence}">'
            f"<title>{interface.side} end; {interface.polarity}; word 5\u2032 to 3\u2032; "
            f"{interface.distance_bp} bp to the supplied stem</title>"
        )
        rows.append(f'<path d="M{x},{by + 5} V{by} H{z} V{by + 5}" fill="none" stroke="#AE6820"/>')
        text(min(x, z), by - 8, f"{interface.sequence} · {interface.distance_bp} bp", "#8C5318")
        overhang = [point(a) for a in interface.overhang]
        lo, hi = min(a for a, _ in overhang) - 7, max(a for a, _ in overhang) + 7
        top = min(b for _, b in overhang) - 12
        rows.append(
            f'<rect data-overhang="{interface.side}" x="{lo}" y="{top}" '
            f'width="{hi - lo}" height="25" rx="3" fill="#AE6820" fill-opacity=".18"/>'
        )
        rows.append("</g>")
    rows.append("</g>")
    return "".join(rows)
