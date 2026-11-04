"""Compact input names; complete terminal chemistry stays attached as metadata."""

from html import escape

from hop_design.models.construction.projections.atlas import AtlasMaterialInput

from ...labels import drawing_material_label, terminal_label
from ..label_layout import LabelPlacer
from .style import INK, TERMINAL_SIZE


def material_label(
    item: AtlasMaterialInput,
    box: tuple[float, float, float, float],
    labels: LabelPlacer,
    *,
    cue: str = "",
) -> str:
    chemistry = [
        terminal_label("5\u2032", item.material.five_prime_end),
        terminal_label("3\u2032", item.material.three_prime_end),
    ]
    modifications = [value for value in chemistry if not value.endswith("OH")]
    name = " · ".join([drawing_material_label(item.material_use.role), *modifications])
    lines = [("material-name", name, INK, TERMINAL_SIZE)]
    if cue:
        lines.append(("material-context", cue, INK, TERMINAL_SIZE))
    left, top, width, height = box
    # An incoming copy-dependent primer sits above the upper handle. Place its
    # cue beside that silhouette, never under the other primer's name.
    x, y = (
        (left + width + 24, top + TERMINAL_SIZE)
        if cue
        else (left, top + height + TERMINAL_SIZE + 8)
    )
    block = labels.block(x, y, lines)
    return block.replace(
        'data-annotation-block="true"',
        'data-annotation-block="true" data-primer-chemistry="'
        + escape(" → ".join(chemistry), quote=True)
        + '"',
        1,
    )
