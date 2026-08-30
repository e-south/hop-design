"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/complete_svg.py

Renders verified whole-route construction summaries as restrained SVGs.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import SearchCompletionStatus
from hop_design.models.construction.projections import CompleteConstructionSummaryProjection

from .svg_common import escape, render_document, short_id


def render_complete_projection_svg(
    projection: CompleteConstructionSummaryProjection,
) -> bytes:
    """Render every examined complete-route disposition without ranking."""
    if projection.status is SearchCompletionStatus.COMPLETE:
        count = projection.accounting.valid_realizations
        noun = "realization" if count == 1 else "realizations"
        title = f"Whole-route composition resolved {count} exact construction {noun}."
    elif projection.status is SearchCompletionStatus.INFEASIBLE:
        title = "No complete construction route resolved after exhaustive composition."
    else:
        title = "Whole-route composition stopped before the declared space was exhausted."
    rows = []
    for index, row in enumerate(projection.rows):
        y = 248 + index * 34
        basal = short_id(row.basal_realization_id) if row.basal_realization_id else "none"
        geometry = short_id(row.achieved_geometry_group_key) or "—"
        product = short_id(row.final_product_group_key) or "—"
        outcome = (
            row.status.value
            if row.rejection_reason is None
            else f"{row.status.value}: {row.rejection_reason.value}"
        )
        rows.append(
            f'<g data-ordinal="{row.ordinal}" data-disposition="{row.status.value}" '
            f'data-foldback-realization-id="{escape(row.foldback_realization_id)}" '
            f'data-basal-realization-id="{escape(row.basal_realization_id or "")}" '
            f'data-materialized-realization-id="{escape(row.materialized_realization_id or "")}" '
            f'data-geometry-group-key="{escape(row.achieved_geometry_group_key or "")}" '
            f'data-final-product-group-key="{escape(row.final_product_group_key or "")}">'
            f'<text x="72" y="{y}" class="body">{row.ordinal}</text>'
            f'<text x="130" y="{y}" class="body">'
            f"{escape(short_id(row.foldback_realization_id))}</text>"
            f'<text x="320" y="{y}" class="body">{escape(basal)}</text>'
            f'<text x="500" y="{y}" class="body">{escape(outcome)}</text>'
            f'<text x="820" y="{y}" class="body">{escape(geometry)}</text>'
            f'<text x="980" y="{y}" class="body">{escape(product)}</text></g>'
        )
    claim = projection.claim_boundary
    summary = (
        f"Nominal {projection.accounting.nominal_combinations} · "
        f"examined {projection.accounting.examined_combinations} · "
        f"accepted {projection.accounting.valid_realizations} · "
        f"rejected {projection.accounting.rejected_combinations}"
    )
    evidence_boundary = (
        "Digital route derivation was verified; physical construction was not recorded."
    )
    order_note = (
        "Every examined combination appears once in canonical Cartesian order; "
        "grouping remains reversible."
    )
    body = f"""
<g data-status="{projection.status.value}" data-endpoint="{projection.endpoint.value}"
data-projection-id="{projection.projection_id}"
data-result-id="{projection.source_result_id}"
data-hop-version="{escape(projection.provenance.hop_version)}"
data-renderer-version="{projection.renderer_version}"
data-digital-design="{claim.digital_design.value}"
data-method="{claim.method.value}"
data-physical-construction="{claim.physical_construction.value}"
data-quality-control="{claim.quality_control.value}"
data-biological-activity="{claim.biological_activity.value}">
<text x="72" y="60" class="title">{escape(title)}</text>
<text x="72" y="100" class="subtitle">{escape(summary)}</text>
<text x="72" y="132" class="small">{evidence_boundary}</text>
</g>
<line x1="72" y1="158" x2="1128" y2="158" class="rule"/>
<text x="72" y="202" class="label">Ordinal</text>
<text x="130" y="202" class="label">Foldback</text>
<text x="320" y="202" class="label">Basal</text>
<text x="500" y="202" class="label">Disposition</text>
<text x="820" y="202" class="label">Geometry</text>
<text x="980" y="202" class="label">Product</text>
{"".join(rows)}
<text x="72" y="{max(300, 248 + len(rows) * 34 + 34)}"
class="small">{order_note}</text>
"""
    return render_document(
        title=title,
        body=body,
        height=max(370, 340 + len(rows) * 34),
        description="Neutral scientific projection of verified whole-route composition.",
    )


__all__ = ["render_complete_projection_svg"]
