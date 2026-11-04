"""Exact external materials, distinct from incorporated molecular occurrences."""

from dataclasses import dataclass
from html import escape

from hop_design.models.construction.projections.atlas import AtlasMaterialInput

from ...labels import drawing_material_label, terminal_label
from ..label_layout import LabelPlacer
from .material_labels import material_label
from .primer_shape import outline_box, primer_outline
from .primer_shape import primer_contour as primer_contour
from .ribbon import ribbon_path, ribbon_points
from .style import INK


@dataclass(frozen=True)
class PlacedInput:
    item: AtlasMaterialInput
    positions: tuple[tuple[float, float], ...]
    cue: str = ""
    outward: int = 1


def input_box(
    positions: tuple[tuple[float, float], ...], *, primer: bool = False, outward: int = 1
) -> tuple[float, float, float, float]:
    outline = (
        primer_outline(list(positions), outward=outward)[0]
        if primer
        else ribbon_points(list(positions), 13, terminal_extension=6)
    )
    return outline_box(outline)


def staged_materials(
    inputs: tuple[PlacedInput, ...], labels: LabelPlacer, *, base_size: float = 16
) -> str:
    rows = []
    for placed in inputs:
        item, positions = placed.item, list(placed.positions)
        box = input_box(placed.positions, primer=item.binding is not None, outward=placed.outward)
        rows.append(
            f'<g data-staged-material="{escape(item.material_use.use_id)}" '
            f'data-material-role="{item.material_use.role.value}" '
            f'data-binding-context="{item.binding_context}" '
            f'data-drawing-box="{" ".join(map(str, box))}">'
        )
        if item.binding is not None:
            rows.append(primer_contour(positions, outward=placed.outward))
        else:
            rows.append(
                f'<path d="{ribbon_path(positions, 13, terminal_extension=6)}" '
                f'fill="#409AC0" fill-opacity=".78" stroke="#334B58" stroke-width="1"/>'
            )
        for index, (base, (x, y)) in enumerate(
            zip(item.material.sequence_5prime, positions, strict=True)
        ):
            rows.append(
                f'<text data-input-base-index="{index}" x="{x}" y="{y + 5}" '
                f'font-size="{base_size:g}" text-anchor="middle" fill="{INK}">{base}</text>'
            )
        chemistry = (
            terminal_label("5\u2032", item.material.five_prime_end)
            + " → "
            + terminal_label("3\u2032", item.material.three_prime_end)
        )
        rows.append(material_label(item, box, labels, cue=placed.cue))
        rows.append(
            f"<title>Incoming {escape(drawing_material_label(item.material_use.role))}; "
            f"{chemistry}; {escape(placed.cue or 'not yet associated')}</title></g>"
        )
    return "".join(rows)
