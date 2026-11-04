"""Literal endpoint sequence in its recorded antiparallel pairing frame."""

from html import escape

from hop_design.models.construction.projections.folded_sequence import FoldedSequenceView
from hop_design.models.construction.projections.neighborhoods import molecular_neighborhood
from hop_design.models.construction.projections.product_stages import ProductStageProjection

from ..labels import endpoint_label
from .folded_sequence import CHANGES, CLOSING, INK, OPEN, STEM


def render_variant_endpoint(stage: ProductStageProjection, view: FoldedSequenceView) -> bytes:
    if stage.unavailable_reason or not stage.bases:
        raise ValueError("Endpoint pairing view unavailable: " + str(stage.unavailable_reason))
    lo, hi = min(b.column for b in stage.bases), max(b.column for b in stage.bases)
    width = max(1050, (hi - lo + 1) * 16 + 100)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 310" role="img">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        f'<text x="28" y="30" font-size="22">{escape(endpoint_label(stage.endpoint))}</text>',
        '<text x="28" y="58" font-size="15">Exact product sequence and recorded pairing; '
        "hairpin intermediates are a separate stage.</text>",
    ]
    colors = {"open": OPEN, "closing": CLOSING, "stem": STEM, "unmapped": INK}
    changes = {
        (i, c.observed_offset): CHANGES[c.kind]
        for i, r in enumerate(view.endpoint_sequence_differences)
        for c in r.columns
        if c.observed_offset is not None and c.kind in CHANGES
    }
    for column in stage.pairing_columns:
        x = 55 + (column - lo) * 16
        lines.append(f'<path d="M{x},124 V148" stroke="#A9B5BC"/>')
    for base in stage.bases:
        x, y = 55 + (base.column - lo) * 16, 115 + base.strand_index * 45
        fill = changes.get((base.strand_index, base.product_index), "white")
        lines += [
            f'<g data-base-index="{base.product_index}" data-strand="{base.strand_index}" '
            f'data-region="{base.region}" '
            f'data-neighborhood="{molecular_neighborhood(base.region) or ""}">',
            f'<rect x="{x - 6}" y="{y - 12}" width="13" height="19" fill="{fill}"/>',
            f'<text x="{x - 5}" y="{y + 3}" font-size="16" '
            f'fill="{colors[base.region]}">{base.base}</text></g>',
        ]
    lines += [
        '<text x="23" y="118" font-size="14">5\u2032</text>',
        '<text x="23" y="163" font-size="14">3\u2032</text>',
    ]
    for i, end in enumerate(stage.product.cohesive_ends):
        lines.append(
            f'<text x="28" y="{204 + i * 22}" font-size="15">'
            f"{end.product_end}: 5\u2032 {escape(end.sequence)} 3\u2032; "
            f"{end.overhang_end.value.replace('_', ' ')} overhang</text>"
        )
    lines.append(
        '<text x="28" y="274" font-size="14">Purple: substitution · Green: addition. '
        "Exact sequences include unresolved position correspondences.</text></g></svg>"
    )
    return "\n".join(lines).encode()
