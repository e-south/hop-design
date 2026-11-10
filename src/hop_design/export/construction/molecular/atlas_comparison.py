"""Exact comparison detail beneath the route; no inferred molecular states."""

from html import escape

from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.projections.atlas import AtlasComparison

from ..labels import material_role_label


def comparison_detail(comparison: AtlasComparison, y: float) -> tuple[str, float]:
    rows: list[str] = []

    def line(text: str, *, size: int = 14, mono: bool = False) -> None:
        nonlocal y
        font = ' font-family="monospace"' if mono else ""
        rows.append(f'<text x="28" y="{y}" font-size="{size}"{font}>{escape(text)}</text>')
        y += size + 9

    def sequence(label: str, value: str) -> None:
        chunks = [value[i : i + 80] for i in range(0, len(value), 80)] or ["∅"]
        for i, chunk in enumerate(chunks):
            line(f"{label if i == 0 else ' ' * len(label)} {chunk}", mono=True)

    line("Exact molecular and material differences", size=18)
    line("Reference → selected: regional sequence changes.")
    for label, regions in (
        ("Hairpin", comparison.regions),
        ("Endpoint", comparison.endpoint_regions),
    ):
        for region in regions:
            if region.reference_sequence == region.observed_sequence:
                continue
            rows.append(
                f'<g data-region-comparison="{escape(region.region)}" data-stage="{label.lower()}">'
            )
            uncertain = region.correspondence in ("ambiguous_minimum_edit", "unresolved_budget")
            counts = {
                kind: sum(c.kind == kind for c in region.columns)
                for kind in ("substitution", "added", "removed")
            }
            explanation = (
                "positional correspondence unresolved"
                if uncertain
                else "; ".join(f"{count} {kind}" for kind, count in counts.items() if count)
            )
            line(f"{label} · {region.region.replace('_', ' ')} · {explanation}")
            sequence("Reference", region.reference_sequence)
            sequence("Selected ", region.observed_sequence)
            rows.append("</g>")
            y += 8
    for material in comparison.materials:
        rows.append(f'<g data-material-comparison="{escape(material.role)}">')
        line(material_role_label(MaterialUseRole(material.role)).capitalize())
        for label, value in (("Reference", material.reference), ("Selected ", material.observed)):
            if value is None:
                line(f"{label}: not used")
            else:
                sequence(label, value.sequence_5prime)
                line(f"5\u2032 {value.five_prime_end.value}; 3\u2032 {value.three_prime_end.value}")
        rows.append("</g>")
        y += 8
    return "\n".join(rows), y


def render_atlas_comparison(comparison: AtlasComparison) -> bytes:
    """Exact comparison sheet, separate from the molecular route's camera bounds."""
    details, height = comparison_detail(comparison, 32)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1150 {height + 24}" '
        'role="img" aria-label="Exact molecular and material differences">'
        '<rect width="100%" height="100%" fill="white"/>'
        '<g font-family="Arial, Helvetica, sans-serif" fill="#243740">' + details + "</g></svg>"
    ).encode()
