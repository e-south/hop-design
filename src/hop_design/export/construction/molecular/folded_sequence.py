"""Literal sequence drawings shared by the local editor and deterministic print export."""

from html import escape
from itertools import pairwise

from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.projections.folded_sequence import FoldedSequenceView
from hop_design.models.construction.projections.neighborhoods import molecular_neighborhood

from ..labels import endpoint_label, material_role_label
from ..scaffold.hairpin_layout import HairpinLayout

INK, OPEN, CLOSING, STEM = "#23313B", "#176B9A", "#258365", "#68747D"
CHANGES = {"substitution": "#F0DCF2", "added": "#D3EEE3"}


def render_folded_sequence(
    view: FoldedSequenceView, *, display_label: str, reference_label: str, methods: str = ""
) -> bytes:
    """Show every literal base and recorded pairing, with bounded regional differences."""
    p = view.portrait
    layout = HairpinLayout(p)
    sequence = p.state.molecules[0].sequence
    # Spacing is a drawing convention. Physical structure is not inferred from pixel distances.
    points = [
        (x * 2.4 - 20, (y - 111) * 2.2 + 155) for x, y in map(layout.point, range(len(sequence)))
    ]
    width = max(1050, max(x for x, _ in points) + 120)
    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="240mm" height="120mm" '
        f'viewBox="0 0 {width:.1f} 530" role="img">',
        f"<title>{escape(display_label)}: complete modeled hairpin</title>",
        "<desc>Literal primary sequence in specified pairing architecture. "
        "Construction and preparation records accompany this drawing.</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
    ]

    def text(x: float, y: float, value: str, size: int = 16, color: str = INK) -> None:
        rows.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
            f'fill="{color}">{escape(value)}</text>'
        )

    loop = next(r.observed_sequence for r in view.regions if r.region == "loop")
    text(28, 30, f"{display_label} · loop {loop}", 22)
    text(
        28,
        55,
        "Hairpin " + ("endpoint" if p.stage_role == "endpoint" else "intermediate before copying"),
    )
    text(
        28,
        80,
        f"{p.stem_bp}-bp supplied stem · {p.loop_side_paired_bp} loop-side bp "
        f"· {p.loop_nt}-nt loop",
    )
    if methods:
        text(28, 104, methods, 14)
    region_by_index = {i: r.region for r in view.regions for i in range(*r.observed_span)}
    highlights = {
        r.observed_span[0] + c.observed_offset: c.kind
        for r in view.regions
        for c in r.columns
        if c.observed_offset is not None and c.kind in CHANGES
    }
    for (x, y), (u, v) in pairwise(points):
        rows.append(f'<path d="M{x:.1f},{y:.1f} L{u:.1f},{v:.1f}" stroke="#CBD2D6" fill="none"/>')
    for pair in p.state.pairings:
        x, y = points[pair.left_index]
        u, v = points[pair.right_index]
        dash = "" if pair.kind.value == "watson_crick" else ' stroke-dasharray="3 3"'
        rows.append(
            f'<path d="M{x:.1f},{y + 12:.1f} L{u:.1f},{v - 12:.1f}" '
            f'stroke="#A9B5BC"{dash} data-pair-kind="{pair.kind.value}"/>'
        )
    for i, (base, (x, y)) in enumerate(zip(sequence, points, strict=True)):
        region = region_by_index[i]
        color = (
            STEM
            if region.startswith("stem")
            else CLOSING
            if region.startswith("closing") or region == "loop"
            else OPEN
        )
        fill = CHANGES.get(highlights.get(i, ""), "white")
        rows.append(
            f'<g data-base-index="{i}" data-region="{region}" '
            f'data-neighborhood="{molecular_neighborhood(region) or ""}">'
            f'<rect x="{x - 6:.1f}" y="{y - 10:.1f}" width="12" height="21" fill="{fill}"/>'
        )
        text(x - 5, y + 5, base, 16, color)
        rows.append("</g>")
    x, y = points[0]
    text(x - 28, y + 5, "5\u2032")
    x, y = points[-1]
    text(x - 28, y + 5, "3\u2032")
    text(
        28,
        285,
        "Purple: substituted position · Green: added position · Comparison reference: "
        + reference_label,
        14,
    )
    changed = [r for r in view.regions if r.reference_sequence != r.observed_sequence]
    text(
        28,
        313,
        "Sequence changes: " + (", ".join(r.region.replace("_", " ") for r in changed) or "none"),
    )
    text(
        28,
        341,
        "Changed materials: "
        + (
            ", ".join(material_role_label(MaterialUseRole(r)) for r in view.changed_material_roles)
            or "none"
        ),
        15,
    )
    text(
        28,
        368,
        "Pairing relationships: "
        + ("unchanged" if view.pairing_relationships_unchanged else "changed"),
        15,
    )
    ambiguous = [
        r.region
        for r in changed
        if r.correspondence in ("ambiguous_minimum_edit", "unresolved_budget")
    ]
    if ambiguous:
        text(
            28,
            395,
            "Position correspondence unresolved: "
            + ", ".join(ambiguous)
            + "; see exact regional sequences.",
            14,
        )
    differences = [
        r for r in view.endpoint_sequence_differences if r.reference_sequence != r.observed_sequence
    ]
    label = endpoint_label(view.endpoint_product.reference.endpoint)
    text(
        28,
        422,
        f"Retrieved product: {label}. Sequence "
        + ("differs from reference." if differences else "matches reference."),
        15,
    )
    for i, difference in enumerate(differences[:2]):
        edits = [
            f"{c.observed_offset + 1 if c.observed_offset is not None else 'deleted'}: "
            f"{c.reference_base or '-'}→{c.observed_base or '-'}"
            for c in difference.columns
            if c.kind != "unchanged"
        ]
        detail = ", ".join(edits[:12]) or "Position correspondence unresolved; see exact sequences."
        if len(edits) > 12:
            detail += f"; {len(edits) - 12} further changes in exact record"
        text(
            28,
            448 + 23 * i,
            f"{difference.region.replace('_', ' ')} (1-based, 5\u2032→3\u2032): {detail}",
            14,
        )
    text(
        28,
        510,
        (
            "Released ends belong to the later product; see its staged drawing."
            if p.later_release is not None
            else "Hairpin endpoint."
            if p.stage_role == "endpoint"
            else "See the staged drawing for the supported downstream product."
        ),
        13,
    )
    rows.append("</g></svg>")
    return "\n".join(rows).encode()
