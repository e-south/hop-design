"""A source-only footprint explanation; not a diagram of an unmade complete molecule."""

from html import escape
from typing import Any


def render_primer_boundary(row: dict[str, Any]) -> bytes:
    sequence = row["source_sequence"]
    a, z = row["stem_span"]
    lo, hi = row["available_span"]
    rlo, rhi = row["required_span"]
    # Preserve exact nucleotide spacing, including a footprint beyond the source.
    origin = 28 + max(0, -rlo) * 12
    width = origin + max(len(sequence), rhi) * 12 + 28

    def bracket(start: int, end: int, y: int, color: str, label: str) -> str:
        x, x2 = origin + start * 12 - 6, origin + end * 12 - 6
        return (
            f'<path d="M {x} {y + 4} v -8 H {x2} v 8" fill="none" stroke="{color}"/>'
            f'<text x="{(x + x2) / 2}" y="{y - 10}" text-anchor="middle" '
            f'font-size="12" fill="{color}">{escape(label)}</text>'
        )

    letters = "".join(
        f'<text x="{origin + i * 12}" y="114" text-anchor="middle">{base}</text>'
        for i, base in enumerate(sequence)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 180" role="img" '
        'aria-label="Examined source geometry and rejected primer footprint">'
        '<rect width="100%" height="100%" fill="white"/>'
        '<g font-family="Arial, sans-serif" fill="#243740">'
        f'<text x="20" y="24" font-size="15">Examined source · {row["primer"]} primer · '
        f"{row['available_nt']} nt available; {row['required_nt']} nt required</text>"
        f'<rect x="{origin + a * 12 - 6}" y="94" width="{(z - a) * 12}" '
        'height="28" rx="3" fill="#F0C9CE" fill-opacity=".65"/>'
        + bracket(rlo, rhi, 68, "#9D5138", "Required footprint")
        + bracket(lo, hi, 91, "#2A7185", "Available flank")
        + f'<g font-family="monospace" font-size="13">{letters}</g>'
        '<text x="20" y="142" font-size="12">Shaded: supplied stem. '
        "Primer binding must remain outside it.</text>"
        '<text x="20" y="166" font-size="12">This examined continuation fails. '
        "No complete failed product is drawn.</text>"
        "</g></svg>"
    ).encode()


def render_primer_boundaries(rows: list[dict[str, Any]]) -> bytes:
    """Export one example per primer/length condition; retain every exact row in JSON."""
    from xml.etree import ElementTree as ET

    distinct = {(r["primer"], r["required_nt"], r["available_nt"]): r for r in rows}
    y, width, groups = 0.0, 800.0, []
    for key in sorted(distinct):
        root = ET.fromstring(render_primer_boundary(distinct[key]))
        _, _, w, h = map(float, root.attrib["viewBox"].split())
        root.tag = "g"
        root.attrib = {"transform": f"translate(0 {y})"}
        groups.append(ET.tostring(root, encoding="unicode"))
        width, y = max(width, w), y + h
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {max(y, 180)}">'
        + "".join(groups)
        + "</svg>"
    ).encode()
