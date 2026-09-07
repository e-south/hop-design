"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/trajectory_partition_svg.py

Renders an exact source-partition certificate inside a route trajectory SVG.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.projections import (
    CompleteConstructionTrajectoryProjection,
)
from hop_design.models.construction.source_partition import SourcePartitionBoundaryKind

from .svg_common import escape


def render_trajectory_partition_rows(
    projection: CompleteConstructionTrajectoryProjection,
    *,
    y_start: int,
) -> tuple[str, int]:
    """Render the selected full-span partition certificate when the route binds one."""
    certificate = projection.source_partition_certificate
    binding = projection.realization.source_partition_binding
    if certificate is None or binding is None:
        return "", 0
    rows = [
        f'<g data-source-partition-binding-id="{escape(binding.binding_id)}" '
        f'data-source-partition-result-id="{escape(binding.result_id)}" '
        f'data-source-partition-realization-id="{escape(binding.realization_id)}" '
        f'data-selected-maximum-sacrificial-fragment-nt="'
        f'{certificate.selected_maximum_sacrificial_fragment_nt}">'
        f'<text x="72" y="{y_start}" class="label">Exact source partition</text>'
        f'<text x="390" y="{y_start}" class="small">'
        f"least-permissive passing maximum · "
        f"{certificate.selected_maximum_sacrificial_fragment_nt} nt</text>"
    ]
    for index, fragment in enumerate(certificate.fragments):
        left = _boundary_label(
            fragment.left_boundary.kind,
            fragment.left_boundary.enzyme_ids,
        )
        right = _boundary_label(
            fragment.right_boundary.kind,
            fragment.right_boundary.enzyme_ids,
        )
        y = y_start + 30 + index * 20
        rows.append(
            f'<text x="122" y="{y}" class="small" data-layout-row="bounded" '
            f'data-partition-fragment-id="{escape(fragment.fragment_id)}" '
            f'data-precursor-strand="{escape(fragment.precursor_strand.value)}" '
            f'data-source-start="{fragment.source_span.start.offset}" '
            f'data-source-end="{fragment.source_span.end.offset}" '
            f'data-fragment-length-nt="{fragment.length_nt}" '
            f'data-fragment-disposition="{escape(fragment.disposition.value)}">'
            f"{escape(fragment.precursor_strand.value)} · "
            f"{fragment.source_span.start.offset}-{fragment.source_span.end.offset} · "
            f"{fragment.length_nt} nt · {escape(fragment.disposition.value)} · "
            f"{escape(left)} → {escape(right)}</text>"
        )
    rows.append("</g>")
    return "".join(rows), 58 + len(certificate.fragments) * 20


def _boundary_label(kind: SourcePartitionBoundaryKind, values: tuple[str, ...]) -> str:
    if kind is SourcePartitionBoundaryKind.PHYSICAL_END:
        return "physical end"
    return "/".join(value.removesuffix("@1").rsplit("/", 1)[-1] for value in values)
