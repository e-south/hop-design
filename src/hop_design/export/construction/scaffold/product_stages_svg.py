"""One compact hairpin-to-endpoint view from recorded regions and strand coordinates."""

from html import escape
from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.product_stages import ProductStageProjection

from ..hairpin_svg import BLUE, GREEN, GREY, INK
from ..labels import endpoint_label


def render_product_stages_svg(p: ProductStageProjection, hairpin_svg: bytes) -> bytes:
    root = ET.fromstring(hairpin_svg)
    shape = next(e for e in root.iter() if e.get("id") == "hairpin-shape")
    for element in list(shape):
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "text":
            if element.text in ("5\u2032", "3\u2032"):
                element.set("font-size", "24")
            else:
                shape.remove(element)
        elif tag == "path" and element.get("data-backbone-index") is None:
            shape.remove(element)
    rows = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="180mm" height="54mm" '
        'viewBox="0 0 900 270">',
        '<rect width="900" height="270" fill="white"/>',
        f'<g font-family="Arial, Helvetica, sans-serif" fill="{INK}" '
        f'data-endpoint="{p.endpoint.value}">',
        '<text x="25" y="30" font-size="19">Which molecule will I obtain?</text>',
        f'<text x="25" y="61" font-size="16">Hairpin {p.hairpin_role}</text>',
        '<g transform="translate(0,20) scale(0.65)">',
        ET.tostring(shape, encoding="unicode"),
        "</g>",
    ]
    if p.unavailable_reason:
        rows += [
            f'<text x="450" y="100" font-size="16">{escape(endpoint_label(p.endpoint))}</text>',
            '<text x="450" y="130" font-size="14">Compact endpoint view unavailable.</text>',
            '<text x="25" y="207" font-size="13">'
            "Exact product, chemistry and reason remain in summary.json.</text>",
        ]
    elif p.hairpin_role == "intermediate":
        lo = min(b.column for b in p.bases)
        hi = max(b.column for b in p.bases)
        pitch = 365 / max(1, hi - lo + 1)
        colors = {"open": BLUE, "stem": GREY, "closing": GREEN, "unmapped": INK}
        label = "Released duplex insert" if p.product.cohesive_ends else "Copied duplex endpoint"
        rows += [
            '<text x="411" y="110" font-size="25">→</text>',
            f'<text x="485" y="61" font-size="16">{label}</text>',
            '<g id="endpoint-shape">',
        ]
        lookup = {(b.strand_index, b.product_index): b for b in p.bases}
        for base in p.bases:
            x, y = 485 + (base.column - lo) * pitch, 94 + base.strand_index * 24
            adjacent = lookup.get((base.strand_index, base.product_index + 1))
            if adjacent is not None:
                x2 = 485 + (adjacent.column - lo) * pitch
                rows.append(
                    f'<line x1="{x:.3f}" x2="{x2:.3f}" y1="{y}" y2="{y}" '
                    f'stroke="{colors[base.region]}" stroke-width="2.5" '
                    f'data-strand-index="{base.strand_index}" '
                    f'data-product-index="{base.product_index}"/>'
                )
        for column in p.pairing_columns:
            x = 485 + (column - lo) * pitch
            rows.append(
                f'<line x1="{x:.3f}" x2="{x:.3f}" y1="94" y2="118" stroke="{GREY}" '
                f'stroke-width="0.6"/>'
            )
        rows += [
            "</g>",
            '<text x="466" y="97" font-size="12">5\u2032</text>',
            '<text x="466" y="121" font-size="12">3\u2032</text>',
            '<text x="855" y="97" font-size="12">3\u2032</text>',
            '<text x="855" y="121" font-size="12">5\u2032</text>',
        ]
        for i, end in enumerate(p.product.cohesive_ends):
            rows.append(
                f'<text x="485" y="{157 + i * 23}" font-size="14">'
                f"{end.product_end}: 5\u2032 {escape(end.sequence)} 3\u2032; "
                f"{end.overhang_end.value.replace('_', ' ')} overhang</text>"
            )
        rows += [
            '<text x="25" y="207" font-size="14">'
            + (
                "Copying + release; ends are exposed only on the released insert."
                if p.product.cohesive_ends
                else "Copying produces the requested duplex."
            )
            + "</text>"
        ]
    else:
        rows += [
            '<text x="450" y="100" font-size="16">This hairpin is the requested endpoint.</text>',
            '<text x="450" y="130" font-size="14">No later released ends are inferred.</text>',
        ]
    rows += [
        '<text x="25" y="238" font-size="13">Region correspondence follows recorded '
        "lineage; drawings use separate scales.</text>",
        "</g></svg>",
    ]
    return "\n".join(rows).encode()
