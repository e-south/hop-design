"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/svg.py

Renders publication-oriented SVGs from typed local construction projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import NamedTuple

from hop_design.models.construction import ConstructionEndpoint, SearchCompletionStatus
from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalFeasibilityRow,
    CompleteConstructionSummaryProjection,
    CompleteConstructionTrajectoryProjection,
    FoldbackFeasibilityProjection,
    LocalScientificProjection,
    RelaxationFrontierProjection,
)

from .complete_svg import render_complete_projection_svg
from .svg_common import ACCENT, WASH
from .svg_common import escape as _escape
from .svg_common import render_document as _document
from .trajectory_svg import render_complete_trajectory_svg


class _BasalGroupKey(NamedTuple):
    nick_strand: str
    nick_offset_nt: int
    type_iis_cut_offset_nt: int | None
    pairing_profile: str | None
    retained_nt: int
    transient_nt: int
    auxiliary_nt: int
    cohesive_end_count: int


def render_projection_svg(
    projection: (
        LocalScientificProjection
        | CompleteConstructionSummaryProjection
        | CompleteConstructionTrajectoryProjection
    ),
) -> bytes:
    """Render one scientific relation without molecular recomputation or ranking."""
    if isinstance(projection, CompleteConstructionSummaryProjection):
        return render_complete_projection_svg(projection)
    if isinstance(projection, CompleteConstructionTrajectoryProjection):
        return render_complete_trajectory_svg(projection)
    if isinstance(projection, FoldbackFeasibilityProjection):
        return _render_foldback(projection)
    if isinstance(projection, BasalFeasibilityProjection):
        return _render_basal(projection)
    if isinstance(projection, RelaxationFrontierProjection):
        return _render_relaxation(projection)
    raise TypeError(f"Unsupported scientific projection: {type(projection).__name__}")


def _render_foldback(projection: FoldbackFeasibilityProjection) -> bytes:
    title = _feasibility_title("Foldback", projection.status, projection.realization_count)
    grouped: dict[tuple[object, ...], list[str]] = {}
    for item in projection.realizations:
        key = (
            item.program_kind,
            item.junction_offset_nt,
            item.loop_length_nt,
            item.annealing_arm_length_bp,
            item.retained_construction_nt,
            item.transient_construction_nt,
        )
        grouped.setdefault(key, []).append(item.local_realization_id)
    rows = []
    for index, (group_key, realization_ids) in enumerate(grouped.items()):
        program, offset, loop, arm, retained, transient = group_key
        y = 236 + index * 38
        geometry = (
            f"offset {offset} nt · loop {loop} nt · arm {arm} bp · "
            f"retained {retained} nt · transient {transient} nt"
        )
        rows.append(
            f'<g data-realization-count="{len(realization_ids)}" '
            f'data-realization-ids="{_escape(" ".join(realization_ids))}">'
            f'<text x="72" y="{y}" class="body">{_escape(program)}</text>'
            f'<text x="360" y="{y}" class="body">{_escape(geometry)}</text>'
            f'<text x="1080" y="{y}" class="body">n={len(realization_ids)}</text></g>'
        )
    body = (
        _status_header(projection, title)
        + f"""
<text x="72" y="188" class="label">Exact compatible realizations</text>
{"".join(rows)}
<text x="72" y="{max(282, 236 + len(rows) * 38 + 30)}" class="small">
Rows group identical observed dimensions; exact membership remains in the tidy outputs.</text>
"""
    )
    return _document(title=title, body=body, height=max(360, 330 + len(rows) * 38))


def _render_basal(projection: BasalFeasibilityProjection) -> bytes:
    endpoint = _endpoint_label(projection.endpoint)
    title = _feasibility_title("Basal", projection.status, projection.realization_count)
    grouped: dict[_BasalGroupKey, list[BasalFeasibilityRow]] = {}
    for item in projection.realizations:
        key = _BasalGroupKey(
            nick_strand=item.nick_strand.value,
            nick_offset_nt=item.nick_offset_nt,
            type_iis_cut_offset_nt=item.type_iis_cut_offset_nt,
            pairing_profile=item.pairing_profile,
            retained_nt=item.retained_nt,
            transient_nt=item.transient_nt,
            auxiliary_nt=item.auxiliary_nt,
            cohesive_end_count=item.cohesive_end_count,
        )
        grouped.setdefault(key, []).append(item)
    rows = []
    for index, (group_key, group_rows) in enumerate(grouped.items()):
        y = 250 + index * 38
        pairing = group_key.pairing_profile or "not required"
        literal_pair_patterns = {
            tuple(
                (pair.source_base, pair.adapter_base, pair.pair_class.value)
                for pair in item.literal_pairs
            )
            for item in projection.realizations
            if item in group_rows
        }
        if literal_pair_patterns:
            pairing += f" · {len(literal_pair_patterns)} literal pair patterns"
        route = f"{group_key.nick_strand} strand · offset {group_key.nick_offset_nt} nt"
        if group_key.type_iis_cut_offset_nt is not None:
            route += f" · Type IIS offset {group_key.type_iis_cut_offset_nt} nt"
        end_pairs = {
            tuple(
                (end.product_end, end.sequence, end.overhang_end.value)
                for end in item.cohesive_ends
            )
            for item in projection.realizations
            if item in group_rows
        }
        ends = f" · {len(end_pairs)} distinct left/right end pairs" if end_pairs else ""
        material = (
            f"retained {group_key.retained_nt} nt · "
            f"transient {group_key.transient_nt} nt · "
            f"auxiliary {group_key.auxiliary_nt} nt · "
            f"cohesive ends {group_key.cohesive_end_count}{ends}"
        )
        realization_ids = [item.local_realization_id for item in group_rows]
        rows.append(
            f'<g data-realization-count="{len(realization_ids)}" '
            f'data-realization-ids="{_escape(" ".join(realization_ids))}">'
            f'<text x="72" y="{y}" class="body">{_escape(route)}</text>'
            f'<text x="360" y="{y}" class="body">{_escape(pairing)}</text>'
            f'<text x="720" y="{y}" class="body">{_escape(material)}</text>'
            f'<text x="1080" y="{y}" class="body">n={len(realization_ids)}</text></g>'
        )
    body = (
        _status_header(projection, title)
        + f"""
<text x="72" y="168" class="subtitle">Requested endpoint: {_escape(endpoint)}</text>
<text x="72" y="206" class="label">Pairing and exact material accounting</text>
{"".join(rows)}
<text x="72" y="{max(296, 250 + len(rows) * 38 + 30)}" class="small">
Rows group identical observed dimensions; no preference is inferred.</text>
"""
    )
    return _document(title=title, body=body, height=max(380, 350 + len(rows) * 38))


def _render_relaxation(projection: RelaxationFrontierProjection) -> bytes:
    first_hit = next((shell.radius for shell in projection.shells if shell.realization_count), None)
    if first_hit == 0:
        title = "Feasibility was present at the requested geometry."
    elif first_hit == 1:
        title = "Feasibility first appeared one step from the requested geometry."
    elif first_hit is not None:
        title = f"Feasibility first appeared {first_hit} steps from the requested geometry."
    elif projection.status is SearchCompletionStatus.INFEASIBLE:
        title = "No feasible realization was found across the complete relaxation frontier."
    else:
        title = "The relaxation frontier ended before feasibility was established."
    scale_width = 920
    interval = scale_width / max(1, len(projection.shells) - 1)
    shells = []
    for index, shell in enumerate(projection.shells):
        x = 140 + index * interval
        ids = " ".join(shell.realization_ids)
        failures = ";".join(f"{reason.code}:{reason.count}" for reason in shell.failure_reasons)
        shells.append(
            f'<g data-radius="{shell.radius}" data-shell-status="{shell.status}" '
            f'data-candidate-count="{shell.candidate_count}" '
            f'data-realization-count="{shell.realization_count}" '
            f'data-rejected-count="{shell.rejected_count}" '
            f'data-failure-reasons="{_escape(failures)}" '
            f'data-realization-ids="{_escape(ids)}">'
            f'<circle cx="{x:.1f}" cy="260" r="22" '
            f'fill="{ACCENT if shell.realization_count else WASH}" '
            f'stroke="{ACCENT}" stroke-width="2"/>'
            f'<text x="{x:.1f}" y="266" text-anchor="middle" class="body">'
            f"{shell.realization_count}</text>"
            f'<text x="{x:.1f}" y="306" text-anchor="middle" class="small">'
            f"radius {shell.radius} · {shell.status} shell</text>"
            f'<text x="{x:.1f}" y="330" text-anchor="middle" class="small">'
            f"{shell.candidate_count} candidates · {shell.rejected_count} rejected</text></g>"
        )
    coordinates = ", ".join(projection.coordinate_names) or "no relaxed coordinates"
    body = (
        _status_header(projection, title)
        + f"""
<text x="72" y="174" class="subtitle">Relaxed coordinates: {_escape(coordinates)}</text>
<line x1="140" y1="260" x2="1060" y2="260" class="rule"/>
{"".join(shells)}
<text x="72" y="378" class="small">Candidate, accepted, rejected, and primary failure counts
replay the source shell accounting; exact realization membership remains in SVG data.</text>
"""
    )
    return _document(title=title, body=body, height=438)


def _feasibility_title(family: str, status: SearchCompletionStatus, count: int) -> str:
    lower = family.lower()
    if status is SearchCompletionStatus.COMPLETE:
        noun = "realization" if count == 1 else "realizations"
        return (
            f"{family} discovery identified {count} exact local route {noun} "
            "under the declared molecular model."
        )
    if status is SearchCompletionStatus.INFEASIBLE:
        return f"No compatible local {lower} route was identified after exhaustive search."
    return f"{family} discovery was truncated with {count} observed exact local route realizations."


def _status_header(
    projection: LocalScientificProjection,
    title: str,
) -> str:
    claims = projection.claim_boundary
    return f"""
<g data-status="{projection.status.value}" data-endpoint="{projection.endpoint.value}"
data-projection-id="{projection.projection_id}"
data-result-id="{projection.source_result_id}"
data-hop-version="{_escape(projection.provenance.hop_version)}"
data-renderer-version="{_escape(projection.renderer_version)}"
data-digital-design="{claims.digital_design.value}"
data-method="{claims.method.value}"
data-physical-construction="{claims.physical_construction.value}"
data-quality-control="{claims.quality_control.value}"
data-biological-activity="{claims.biological_activity.value}">
<text x="72" y="60" class="title">{_escape(title)}</text>
<text x="72" y="98" class="subtitle">Status: {_escape(projection.status.value)}</text>
<text x="72" y="128" class="small">Local feasibility only; complete route composition and
physical construction are not established.</text>
</g>
<line x1="72" y1="150" x2="1128" y2="150" class="rule"/>
"""


def _endpoint_label(endpoint: ConstructionEndpoint) -> str:
    return {
        ConstructionEndpoint.SSDNA_HAIRPIN: "single-stranded hairpin endpoint",
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX: "hairpin PCR duplex endpoint",
        ConstructionEndpoint.CLONE_READY_DUPLEX: "clone-ready duplex endpoint",
    }[endpoint]
