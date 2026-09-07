"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/foldback_svg.py

Renders foldback-neighborhood feasibility projections as publication-oriented SVG.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import NamedTuple

from hop_design.models.construction.projections import FoldbackFeasibilityProjection

from .local_svg_common import feasibility_title, status_header
from .svg_common import escape, render_document


class _FoldbackGroupKey(NamedTuple):
    program_kind: str
    nick_strand: str
    source_orientation: str
    junction_offset_nt: int
    loop_length_nt: int
    annealing_arm_length_bp: int
    retained_overhead_nt: int
    transient_construction_nt: int


def render_foldback_projection_svg(projection: FoldbackFeasibilityProjection) -> bytes:
    """Render exact foldback realization groups without ranking or selection."""
    title = feasibility_title(
        "Foldback",
        projection.disposition.completion,
        projection.disposition.feasibility,
        projection.realization_count,
        projection.sequence_partition,
    )
    grouped: dict[_FoldbackGroupKey, list[str]] = {}
    for item in projection.realizations:
        key = _FoldbackGroupKey(
            program_kind=item.program_kind.value,
            nick_strand=item.nick_strand.value,
            source_orientation=item.source_orientation.value,
            junction_offset_nt=item.junction_offset_nt,
            loop_length_nt=item.loop_length_nt,
            annealing_arm_length_bp=item.annealing_arm_length_bp,
            retained_overhead_nt=item.retained_overhead_nt,
            transient_construction_nt=item.transient_construction_nt,
        )
        grouped.setdefault(key, []).append(item.local_realization_id)
    rows = []
    for index, (group_key, realization_ids) in enumerate(grouped.items()):
        program, nick_strand, source_orientation, offset, loop, arm, retained, transient = group_key
        y = 236 + index * 38
        route = f"{nick_strand} strand · {source_orientation.replace('_', '-')} source"
        geometry = (
            f"offset {offset} nt · loop {loop} nt · arm {arm} bp · "
            f"retained {retained} nt · transient {transient} nt"
        )
        rows.append(
            f'<g data-realization-count="{len(realization_ids)}" '
            f'data-realization-ids="{escape(" ".join(realization_ids))}">'
            f'<text x="72" y="{y}" class="body">{escape(program)}</text>'
            f'<text x="300" y="{y}" class="body">{escape(route)}</text>'
            f'<text x="600" y="{y}" class="body">{escape(geometry)}</text>'
            f'<text x="1080" y="{y}" class="body">n={len(realization_ids)}</text></g>'
        )
    body = (
        status_header(projection, title)
        + f"""
<text x="72" y="188" class="label">Exact realizations satisfying declared constraints</text>
{"".join(rows)}
<text x="72" y="{max(282, 236 + len(rows) * 38 + 30)}" class="small">
Rows group identical observed dimensions; exact membership remains in the tidy outputs.</text>
"""
    )
    return render_document(title=title, body=body, height=max(360, 330 + len(rows) * 38))
