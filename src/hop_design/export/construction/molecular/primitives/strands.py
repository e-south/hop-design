"""An editable 5\u2032-to-3\u2032 strand drawn at authoritative nucleotide coordinates."""

from collections.abc import Mapping
from html import escape

from hop_design.models.construction.projections.inspection import MolecularStateInspection

from ..inspection_scene import Points, edge
from .style import BASE_SIZE, INK, object_id


def strand_primitives(
    projection: MolecularStateInspection,
    points: Points,
    changes: Mapping[tuple[int, int], str],
    change_colors: dict[str, str],
) -> str:
    rows = []
    for strand_index, strand in enumerate(projection.state.molecules):
        rows.append(
            f'<g id="{object_id("strand", projection.state.state_id, strand.strand_id)}" '
            f'data-strand-primitive="{escape(strand.strand_id)}" '
            'data-sequence-direction="5prime-to-3prime">'
        )
        for i in range(len(strand.sequence) - 1):
            rows.append(edge("backbone", (strand.strand_id, i), (strand.strand_id, i + 1), points))
        for i, base in enumerate(strand.sequence):
            x, y = points[strand.strand_id, i]
            change = changes.get((strand_index, i), "")
            rows.append(
                f'<g data-base-index="{i}" data-strand="{strand_index}" data-change="{change}">'
                f'<rect x="{x - 7}" y="{y - 11}" width="14" height="20" '
                f'fill="{change_colors.get(change, "none")}"/>'
                f'<text x="{x - 5}" y="{y + 5}" font-size="{BASE_SIZE}" '
                f'fill="{INK}">{base}</text></g>'
            )
        rows.append("</g>")
    return "".join(rows)
