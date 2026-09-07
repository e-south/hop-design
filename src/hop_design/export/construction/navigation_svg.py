"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/navigation_svg.py

Renders accepted construction routes and achieved geometry groups as SVG.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import SearchCompletionStatus
from hop_design.models.construction.projections import (
    CompleteConstructionSummaryRow,
    ConstructionNavigationAcceptedRoute,
    ConstructionNavigationProjection,
)

from .svg_common import escape, render_document, short_id


def render_navigation_projection_svg(
    projection: ConstructionNavigationProjection,
) -> bytes:
    """Render accepted routes without ranking or reproducing rejection evidence."""
    summary = projection.summary
    title = _title(projection)
    truncation_notes = _truncation_notes(projection)
    truncation_height = len(truncation_notes) * 22
    geometry_header_y = 190 + truncation_height
    geometry_start_y = 226 + truncation_height
    geometry_rows = []
    for index, group in enumerate(projection.geometry_groups):
        y = geometry_start_y + index * 42
        foldback = group.foldback_geometry
        foldback_text = (
            f"{foldback.nick_strand.value} strand · offset "
            f"{foldback.junction_offset_nt} nt · loop "
            f"{foldback.loop_length_nt} nt · arm {foldback.annealing_arm_length_bp} bp"
        )
        basal = group.basal_geometry
        basal_text = (
            "not required"
            if basal is None
            else (
                f"{basal.nick_strand.value} strand · offset "
                f"{basal.nick_offset_nt} nt · "
                f"{len(basal.pairing_constraints)} paired positions"
            )
        )
        multiplicity = len(group.realization_ids)
        geometry_rows.append(
            f'<g data-geometry-group-key="{escape(group.group_key)}" '
            f'data-realization-count="{multiplicity}" '
            f'data-realization-ids="{escape(" ".join(group.realization_ids))}">'
            f'<text x="72" y="{y}" class="body">{escape(foldback_text)}</text>'
            f'<text x="620" y="{y}" class="body">{escape(basal_text)}</text>'
            f'<text x="1080" y="{y}" class="body">n={multiplicity}</text></g>'
        )

    geometry_height = len(geometry_rows) * 42
    rule_y = 248 + truncation_height + geometry_height
    header_y = 292 + truncation_height + geometry_height
    row_start_y = 338 + truncation_height + geometry_height
    summary_rows = {
        row.materialized_realization_id: row
        for row in summary.rows
        if row.materialized_realization_id is not None
    }
    route_rows = [
        _render_route(route, summary_rows[route.materialized_realization_id], row_start_y + i * 34)
        for i, route in enumerate(projection.accepted_routes)
    ]
    accounting = summary.accounting
    claims = summary.claim_boundary
    accounting_text = (
        f"Examined {accounting.examined_combinations} of {accounting.nominal_combinations} "
        f"combinations · {accounting.valid_realizations} accepted"
    )
    evidence_boundary = (
        "Digital route derivation was verified; physical construction was not recorded."
    )
    body = f"""
<g data-status="{summary.status.value}" data-endpoint="{summary.endpoint.value}"
data-projection-id="{projection.projection_id}"
data-result-id="{projection.source_result_id}"
data-hop-version="{escape(summary.provenance.hop_version)}"
data-renderer-version="{projection.renderer_version}"
data-truncation-reasons="{escape(";".join(summary.truncation_reasons))}"
data-upstream-truncation-reasons="{escape(";".join(summary.upstream_truncation_reasons))}"
data-digital-design="{claims.digital_design.value}"
data-method="{claims.method.value}"
data-physical-construction="{claims.physical_construction.value}"
data-quality-control="{claims.quality_control.value}"
data-biological-activity="{claims.biological_activity.value}">
<text x="72" y="60" class="title">{escape(title)}</text>
<text x="72" y="100" class="subtitle">{escape(accounting_text)}</text>
<text x="72" y="132" class="small">{evidence_boundary}</text>
</g>
{"".join(truncation_notes)}
<text x="72" y="{geometry_header_y}" class="label">Foldback geometry</text>
<text x="620" y="{geometry_header_y}" class="label">Basal geometry</text>
<text x="1080" y="{geometry_header_y}" class="label">Routes</text>
{"".join(geometry_rows)}
<line x1="72" y1="{rule_y}" x2="1128" y2="{rule_y}" class="rule"/>
<text x="72" y="{header_y}" class="label">Ordinal</text>
<text x="150" y="{header_y}" class="label">Foldback</text>
<text x="340" y="{header_y}" class="label">Basal</text>
<text x="520" y="{header_y}" class="label">Geometry</text>
<text x="730" y="{header_y}" class="label">Cleavage enzymes</text>
<text x="980" y="{header_y}" class="label">Product</text>
{"".join(route_rows)}
<text x="72" y="{max(300, row_start_y + len(route_rows) * 34 + 34)}" class="small">
Routes remain in canonical composition order; no preference is inferred.
</text>
"""
    return render_document(
        title=title,
        body=body,
        height=max(460, 430 + truncation_height + geometry_height + len(route_rows) * 34),
        description="Neutral navigation projection of verified whole-route composition.",
    )


def _title(projection: ConstructionNavigationProjection) -> str:
    summary = projection.summary
    if summary.status is SearchCompletionStatus.COMPLETE:
        count = len(projection.accepted_routes)
        noun = "route" if count == 1 else "routes"
        return f"Whole-route composition resolved {count} exact construction {noun}."
    if summary.status is SearchCompletionStatus.INFEASIBLE:
        return "No complete construction route resolved after exhaustive composition."
    return "Whole-route composition stopped before the declared space was exhausted."


def _truncation_notes(projection: ConstructionNavigationProjection) -> list[str]:
    summary = projection.summary
    notes: list[tuple[str, str]] = []
    if summary.truncation_reasons:
        notes.append(
            ("composition", "Composition truncation · " + " · ".join(summary.truncation_reasons))
        )
    if summary.upstream_truncation_reasons:
        notes.append(
            (
                "upstream",
                "Upstream truncation · " + " · ".join(summary.upstream_truncation_reasons),
            )
        )
    return [
        f'<text x="72" y="{164 + index * 22}" class="small" '
        f'data-truncation-scope="{scope}">{escape(note)}</text>'
        for index, (scope, note) in enumerate(notes)
    ]


def _render_route(
    route: ConstructionNavigationAcceptedRoute,
    summary_row: CompleteConstructionSummaryRow,
    y: int,
) -> str:
    basal_id = (
        short_id(summary_row.basal_realization_id) if summary_row.basal_realization_id else "none"
    )
    geometry = short_id(summary_row.achieved_geometry_group_key) or "—"
    product = short_id(summary_row.final_product_group_key) or "—"
    enzymes = ", ".join(route.cleavage_enzyme_ids) or "none"
    return (
        f'<g data-ordinal="{summary_row.ordinal}" '
        f'data-foldback-realization-id="{escape(summary_row.foldback_realization_id)}" '
        f'data-basal-realization-id="{escape(summary_row.basal_realization_id or "")}" '
        f'data-materialized-realization-id="{escape(route.materialized_realization_id)}" '
        f'data-geometry-group-key="{escape(summary_row.achieved_geometry_group_key or "")}" '
        f'data-final-product-group-key="{escape(summary_row.final_product_group_key or "")}" '
        f'data-exact-geometry="{str(route.exact_geometry).lower()}" '
        f'data-cleavage-enzyme-ids="{escape(" ".join(route.cleavage_enzyme_ids))}" '
        f'data-retained-non-payload-nt="{route.retained_non_payload_nt}" '
        f'data-final-product-topology="{escape(route.final_product_topology)}">'
        f'<text x="72" y="{y}" class="body">{summary_row.ordinal}</text>'
        f'<text x="150" y="{y}" class="body">'
        f"{escape(short_id(summary_row.foldback_realization_id))}</text>"
        f'<text x="340" y="{y}" class="body">{escape(basal_id)}</text>'
        f'<text x="520" y="{y}" class="body">{escape(geometry)}</text>'
        f'<text x="730" y="{y}" class="body">{escape(enzymes)}</text>'
        f'<text x="980" y="{y}" class="body">{escape(product)}</text></g>'
    )


__all__ = ["render_navigation_projection_svg"]
