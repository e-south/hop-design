"""Recorded primer binding annotations, without inventing annealed molecular states."""

from html import escape

from hop_design.models.construction.projections.atlas import AtlasMaterialInput

from ..labels import material_role_label, terminal_label
from .label_layout import LabelPlacer
from .primitives.material_labels import material_label
from .primitives.materials import input_box
from .primitives.primer_geometry import outward_side, position_primer
from .primitives.primer_shape import primer_contour
from .primitives.style import INK, object_id


def material_binding_overlays(
    inputs: tuple[AtlasMaterialInput, ...],
    points: dict[tuple[str, int], tuple[float, float]],
    labels: LabelPlacer,
    *,
    base_size: float = 16,
) -> str:
    rows = []
    for item in inputs:
        binding = item.binding
        if binding is None or item.binding_context != "recorded_state":
            continue
        # Binding bases follow the template exactly, including its handle bend.
        template = [
            points[binding.template_strand_id, i]
            for i in reversed(
                range(binding.template_span.start.offset, binding.template_span.end.offset)
            )
        ]
        center = (
            sum(x for x, _ in points.values()) / len(points),
            sum(y for _, y in points.values()) / len(points),
        )
        side = outward_side(template, center)
        sequence = item.material.sequence_5prime
        extra = len(sequence) - len(template)
        positions = position_primer(template, list(points.values()), outward=side, leading=extra)
        bound = positions[extra:]
        left, top, width, height = input_box(tuple(positions), primer=True, outward=side)
        right, bottom = left + width, top + height
        labels.occupied.append((left - 16, top, right - left + 32, bottom - top))
        rows.append(
            f'<g id="{object_id("primer", item.binding_state_id or "", item.material_use.use_id)}" '
            f'data-primer-binding="{escape(item.material_use.use_id)}" '
            f'data-material-role="{item.material_use.role.value}" '
            f'data-template-state="{escape(item.binding_state_id or "")}" '
            f'data-drawing-box="{left - 16} {top} {right - left + 32} {bottom - top}" '
            'data-binding-annotation="true">'
        )
        for (tx, ty), (bx, by) in zip(
            template[:: max(1, len(template) - 1)], bound[:: max(1, len(bound) - 1)], strict=True
        ):
            rows.append(
                f'<path d="M{tx},{ty} L{bx},{by}" fill="none" '
                'stroke="#526A75" stroke-dasharray="3 3" stroke-opacity=".5"/>'
            )
        rows.append(primer_contour(positions, outward=side))
        for i, (base, (bx, by)) in enumerate(zip(sequence, positions, strict=True)):
            rows.append(
                f'<text data-input-base-index="{i}" x="{bx}" y="{by + 5}" '
                f'font-size="{base_size:g}" text-anchor="middle" fill="{INK}">{base}</text>'
            )
        role = material_role_label(item.material_use.role)
        chemistry = (
            terminal_label("5\u2032", item.material.five_prime_end)
            + "; "
            + terminal_label("3\u2032", item.material.three_prime_end)
        )
        rows.append(
            f"<title>{escape(role)}; {chemistry}; {item.annealing_length_nt} nt binding</title>"
        )
        rows.append(material_label(item, (left, top, width, height), labels))
        rows.append("</g>")
    return "".join(rows)
