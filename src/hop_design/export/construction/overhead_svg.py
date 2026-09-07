"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/overhead_svg.py

Renders retained-overhead coverage for local construction discovery as SVG.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import SearchFeasibilityStatus
from hop_design.models.construction.projections import RetainedOverheadFrontierProjection

from .local_svg_common import partition_scope, status_header
from .svg_common import ACCENT, WASH, escape, render_document


def render_retained_overhead_svg(projection: RetainedOverheadFrontierProjection) -> bytes:
    """Render exact retained-overhead coverage and level accounting."""
    first_hit = next(
        (level.retained_overhead_nt for level in projection.levels if level.realization_count),
        None,
    )
    partition = projection.sequence_partition
    scope = partition_scope(partition)
    if first_hit == 0:
        title = f"Feasibility was present with zero retained overhead{scope}."
    elif first_hit == 1:
        title = f"Feasibility first appeared at one retained nucleotide{scope}."
    elif first_hit is not None:
        title = f"Feasibility first appeared at {first_hit} retained nucleotides{scope}."
    elif projection.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE:
        if partition is None:
            title = "No feasible realization was found across the complete overhead envelope."
        else:
            title = f"No feasible realization was found{scope} across its overhead envelope."
    else:
        title = "The overhead search ended before feasibility was established."
    scale_width = 920
    interval = scale_width / max(1, len(projection.levels) - 1)
    levels = []
    for index, level in enumerate(projection.levels):
        x = 140 + index * interval
        ids = " ".join(level.realization_ids)
        failures = ";".join(f"{reason.code}:{reason.count}" for reason in level.failure_reasons)
        levels.append(
            f'<g data-retained-overhead-nt="{level.retained_overhead_nt}" '
            f'data-level-status="{level.status}" '
            f'data-candidate-count="{level.candidate_count}" '
            f'data-realization-count="{level.realization_count}" '
            f'data-rejected-count="{level.rejected_count}" '
            f'data-failure-reasons="{escape(failures)}" '
            f'data-realization-ids="{escape(ids)}">'
            f'<circle cx="{x:.1f}" cy="260" r="22" '
            f'fill="{ACCENT if level.realization_count else WASH}" '
            f'stroke="{ACCENT}" stroke-width="2"/>'
            f'<text x="{x:.1f}" y="266" text-anchor="middle" class="body">'
            f"{level.realization_count}</text>"
            f'<text x="{x:.1f}" y="306" text-anchor="middle" class="small">'
            f"{level.retained_overhead_nt} nt · {level.status} level</text>"
            f'<text x="{x:.1f}" y="330" text-anchor="middle" class="small">'
            f"{level.candidate_count} candidates · {level.rejected_count} rejected</text></g>"
        )
    body = (
        status_header(projection, title)
        + f"""
<text x="72" y="174" class="subtitle">Absolute retained non-payload overhead</text>
<line x1="140" y1="260" x2="1060" y2="260" class="rule"/>
{"".join(levels)}
<text x="72" y="378" class="small">Candidate, accepted, rejected, and primary failure counts
replay the source level accounting; exact realization membership remains in SVG data.</text>
"""
    )
    return render_document(title=title, body=body, height=438)
