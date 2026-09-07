"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/source_partition_svg.py

Renders a nucleotide-coordinate map of one exact source-partition certificate.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.projections import SourcePartitionCertificateProjection
from hop_design.models.construction.source_partition import (
    SourcePartitionFragmentDisposition,
)
from hop_design.models.junction import Strand

from .svg_common import ACCENT, INK, MUTED, RULE, escape, render_document

_SACRIFICIAL = "#d9a06c"


def _enzyme_label(enzyme_id: str) -> str:
    return enzyme_id.removesuffix("@1").rsplit("/", 1)[-1]


def _fragment_rects(projection: SourcePartitionCertificateProjection) -> str:
    certificate = projection.certificate
    left = 170.0
    width = 880.0
    row_y = {Strand.TOP: 222.0, Strand.BOTTOM: 322.0}
    parts: list[str] = []
    for fragment in certificate.fragments:
        x = left + width * fragment.source_span.start.offset / certificate.source_length_nt
        fragment_width = width * fragment.length_nt / certificate.source_length_nt
        y = row_y[fragment.precursor_strand]
        required = fragment.disposition is SourcePartitionFragmentDisposition.REQUIRED
        fill = ACCENT if required else _SACRIFICIAL
        text_fill = "#ffffff" if required else INK
        parts.append(
            f'<g data-fragment-id="{escape(fragment.fragment_id)}" '
            f'data-disposition="{fragment.disposition.value}">'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{fragment_width:.1f}" height="42" '
            f'fill="{fill}" stroke="#ffffff" stroke-width="2"/>'
            f'<text x="{x + fragment_width / 2:.1f}" y="{y + 27:.1f}" '
            f'text-anchor="middle" style="font-size:13px;fill:{text_fill}">'
            f"{fragment.length_nt} nt</text></g>"
        )
    return "".join(parts)


def _cleavage_labels(projection: SourcePartitionCertificateProjection) -> str:
    certificate = projection.certificate
    left = 170.0
    width = 880.0
    row_y = {Strand.TOP: 222.0, Strand.BOTTOM: 322.0}
    seen: set[tuple[Strand, int]] = set()
    labels: list[str] = []
    for fragment in certificate.fragments:
        for boundary in (fragment.left_boundary, fragment.right_boundary):
            key = (fragment.precursor_strand, boundary.source_offset)
            if not boundary.enzyme_ids or key in seen:
                continue
            seen.add(key)
            x = left + width * boundary.source_offset / certificate.source_length_nt
            y = row_y[fragment.precursor_strand]
            label_y = y - 12 if fragment.precursor_strand is Strand.TOP else y + 66
            labels.append(
                f'<g data-strand="{fragment.precursor_strand.value}" '
                f'data-cut-offset="{boundary.source_offset}">'
                f'<line x1="{x:.1f}" y1="{y - 6:.1f}" x2="{x:.1f}" '
                f'y2="{y + 48:.1f}" stroke="{INK}" stroke-width="2"/>'
                f'<text x="{x:.1f}" y="{label_y:.1f}" text-anchor="middle" class="small">'
                f"{escape('/'.join(_enzyme_label(item) for item in boundary.enzyme_ids))} "
                f"· {boundary.source_offset}</text></g>"
            )
    return "".join(labels)


def render_source_partition_projection_svg(
    projection: SourcePartitionCertificateProjection,
) -> bytes:
    """Render one source-coordinate-aligned two-strand fragment certificate."""
    certificate = projection.certificate
    selected = certificate.selected_maximum_sacrificial_fragment_nt
    threshold_labels = " · ".join(
        f"{item.maximum_sacrificial_fragment_nt} nt {'pass' if item.feasible else 'blocked'}"
        for item in certificate.thresholds
    )
    title = "The selected program accounts for every source fragment"
    summary = (
        f"{projection.examined_nodes} of {projection.candidate_space_size} enzyme programs "
        f"examined · selected maximum {selected} nt"
    )
    boundary = (
        "Digital partition under declared cut geometry; physical cleavage and recovery "
        "are not established."
    )
    body = f"""
<g data-result-id="{escape(projection.source_result_id)}"
data-realization-id="{escape(projection.realization_id)}">
<text x="72" y="72" class="title">{escape(title)}</text>
<text x="72" y="108" class="subtitle">{escape(summary)}</text>
<line x1="72" y1="138" x2="1128" y2="138" class="rule"/>
<text x="72" y="205" class="label">Prepared source duplex</text>
<text x="126" y="249" text-anchor="end" class="body">5&#x2032; top</text>
<text x="1074" y="249" class="body">3&#x2032;</text>
<text x="126" y="349" text-anchor="end" class="body">3&#x2032; bottom</text>
<text x="1074" y="349" class="body">5&#x2032;</text>
{_fragment_rects(projection)}
{_cleavage_labels(projection)}
<rect x="72" y="420" width="18" height="18" fill="{ACCENT}"/>
<text x="102" y="435" class="body">Required fragment</text>
<rect x="280" y="420" width="18" height="18" fill="{_SACRIFICIAL}"/>
<text x="310" y="435" class="body">Sacrificial fragment</text>
<line x1="72" y1="468" x2="1128" y2="468" stroke="{RULE}" stroke-width="1.5"/>
<text x="72" y="500" class="label">Inclusive sacrificial-fragment ladder</text>
<text x="72" y="530" class="body">{escape(threshold_labels)}</text>
<text x="72" y="570" class="small" style="fill:{MUTED}">{escape(boundary)}</text>
</g>
"""
    return render_document(
        title=title,
        body=body,
        height=610,
        description=(
            "Exact top- and bottom-strand fragment intervals, cleavage boundaries, and "
            "threshold evidence from one verified source-partition realization."
        ),
    )


__all__ = ["render_source_partition_projection_svg"]
