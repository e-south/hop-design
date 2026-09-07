"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/svg.py

Renders publication-oriented SVGs from typed construction projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import NamedTuple

from hop_design.models.construction import (
    ConstructionEndpoint,
    SearchCompletionStatus,
    SearchFeasibilityStatus,
)
from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalFeasibilityRow,
    BasalMinimumOverheadMatrixProjection,
    CompleteConstructionSummaryProjection,
    CompleteConstructionTrajectoryProjection,
    ConstructionNavigationProjection,
    ConstructionScientificProjection,
    FoldbackFeasibilityProjection,
    LocalScientificProjection,
    RetainedOverheadFrontierProjection,
    SourcePartitionCertificateProjection,
)
from hop_design.models.construction.sequence_domain import SequenceDomainPartition

from .complete_svg import render_complete_projection_svg
from .navigation_svg import render_navigation_projection_svg
from .source_partition_svg import render_source_partition_projection_svg
from .svg_common import ACCENT, WASH
from .svg_common import escape as _escape
from .svg_common import render_document as _document
from .trajectory_svg import render_complete_trajectory_svg


class _BasalGroupKey(NamedTuple):
    nick_enzyme_id: str
    future_release_enzyme_id: str | None
    nick_strand: str
    nick_offset_nt: int
    pairing_pattern: str | None
    retained_overhead_nt: int
    required_annealing_nt: int
    annealing_completion_nt: int
    warning_count: int


class _FoldbackGroupKey(NamedTuple):
    program_kind: str
    nick_strand: str
    source_orientation: str
    junction_offset_nt: int
    loop_length_nt: int
    annealing_arm_length_bp: int
    retained_overhead_nt: int
    transient_construction_nt: int


def render_projection_svg(projection: ConstructionScientificProjection) -> bytes:
    """Render one scientific relation without molecular recomputation or ranking."""
    if isinstance(projection, CompleteConstructionSummaryProjection):
        return render_complete_projection_svg(projection)
    if isinstance(projection, ConstructionNavigationProjection):
        return render_navigation_projection_svg(projection)
    if isinstance(projection, CompleteConstructionTrajectoryProjection):
        return render_complete_trajectory_svg(projection)
    if isinstance(projection, SourcePartitionCertificateProjection):
        return render_source_partition_projection_svg(projection)
    if isinstance(projection, FoldbackFeasibilityProjection):
        return _render_foldback(projection)
    if isinstance(projection, BasalFeasibilityProjection):
        return _render_basal(projection)
    if isinstance(projection, BasalMinimumOverheadMatrixProjection):
        return _render_basal_matrix(projection)
    if isinstance(projection, RetainedOverheadFrontierProjection):
        return _render_retained_overhead(projection)
    raise TypeError(f"Unsupported scientific projection: {type(projection).__name__}")


def _render_foldback(projection: FoldbackFeasibilityProjection) -> bytes:
    title = _feasibility_title(
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
            f'data-realization-ids="{_escape(" ".join(realization_ids))}">'
            f'<text x="72" y="{y}" class="body">{_escape(program)}</text>'
            f'<text x="300" y="{y}" class="body">{_escape(route)}</text>'
            f'<text x="600" y="{y}" class="body">{_escape(geometry)}</text>'
            f'<text x="1080" y="{y}" class="body">n={len(realization_ids)}</text></g>'
        )
    body = (
        _status_header(projection, title)
        + f"""
<text x="72" y="188" class="label">Exact realizations satisfying declared constraints</text>
{"".join(rows)}
<text x="72" y="{max(282, 236 + len(rows) * 38 + 30)}" class="small">
Rows group identical observed dimensions; exact membership remains in the tidy outputs.</text>
"""
    )
    return _document(title=title, body=body, height=max(360, 330 + len(rows) * 38))


def _render_basal(projection: BasalFeasibilityProjection) -> bytes:
    endpoint = _endpoint_label(projection.endpoint)
    title = _feasibility_title(
        "Basal",
        projection.disposition.completion,
        projection.disposition.feasibility,
        projection.realization_count,
        projection.sequence_partition,
    )
    grouped: dict[_BasalGroupKey, list[BasalFeasibilityRow]] = {}
    for item in projection.realizations:
        key = _BasalGroupKey(
            nick_enzyme_id=item.nick_enzyme_id,
            future_release_enzyme_id=item.future_release_enzyme_id,
            nick_strand=item.nick_strand.value,
            nick_offset_nt=item.nick_offset_nt,
            pairing_pattern=item.pairing_pattern,
            retained_overhead_nt=item.retained_overhead_nt,
            required_annealing_nt=item.required_annealing_nt,
            annealing_completion_nt=item.annealing_completion_nt,
            warning_count=len(item.warnings),
        )
        grouped.setdefault(key, []).append(item)
    rows = []
    for index, (group_key, group_rows) in enumerate(grouped.items()):
        y = 250 + index * 38
        pairing = group_key.pairing_pattern or "not required"
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
        release = group_key.future_release_enzyme_id or "not required"
        route = (
            f"{group_key.nick_enzyme_id} · {group_key.nick_strand} strand · "
            f"offset {group_key.nick_offset_nt} nt"
        )
        obligation = (
            f"release {release} · retained overhead {group_key.retained_overhead_nt} nt · "
            f"annealing {group_key.required_annealing_nt} nt "
            f"({group_key.annealing_completion_nt} nt completion)"
        )
        if group_key.warning_count:
            obligation += " · mismatch warning"
        realization_ids = [item.local_realization_id for item in group_rows]
        rows.append(
            f'<g data-realization-count="{len(realization_ids)}" '
            f'data-realization-ids="{_escape(" ".join(realization_ids))}">'
            f'<text x="72" y="{y}" class="body">{_escape(route)}</text>'
            f'<text x="360" y="{y}" class="body">{_escape(pairing)}</text>'
            f'<text x="720" y="{y}" class="body">{_escape(obligation)}</text>'
            f'<text x="1080" y="{y}" class="body">n={len(realization_ids)}</text></g>'
        )
    body = (
        _status_header(projection, title)
        + f"""
<text x="72" y="168" class="subtitle">Requested endpoint: {_escape(endpoint)}</text>
<text x="72" y="206" class="label">Local pairing and upstream completion obligations</text>
{"".join(rows)}
<text x="72" y="{max(296, 250 + len(rows) * 38 + 30)}" class="small">
Rows group identical observed dimensions; no preference is inferred.</text>
"""
    )
    return _document(title=title, body=body, height=max(380, 350 + len(rows) * 38))


def _render_basal_matrix(projection: BasalMinimumOverheadMatrixProjection) -> bytes:
    title = "Basal local accessibility by nickase and future release action"
    left = 300
    top = 252
    matrix_width = 820
    cell_width = matrix_width / len(projection.release_actions)
    cell_height = 44
    palette = (
        "#0d3b2e",
        "#14513f",
        "#176b54",
        "#26846a",
        "#3c9b7d",
        "#62ae92",
        "#8cc2aa",
        "#bad8c9",
        "#e2efe8",
    )
    action_index = {
        action.action_id: index for index, action in enumerate(projection.release_actions)
    }
    nick_index = {enzyme_id: index for index, enzyme_id in enumerate(projection.nick_enzyme_ids)}
    labels = []
    for index, action in enumerate(projection.release_actions):
        x = left + index * cell_width + cell_width / 2
        label = f"{_enzyme_label(action.enzyme_id)} · {action.requirement.orientation.value}"
        labels.append(
            f'<text x="{x:.1f}" y="{top - 22}" text-anchor="middle" class="small">'
            f"{_escape(label)}</text>"
        )
    for index, enzyme_id in enumerate(projection.nick_enzyme_ids):
        y = top + index * cell_height + cell_height / 2 + 5
        labels.append(
            f'<text x="{left - 18}" y="{y:.1f}" text-anchor="end" class="body">'
            f"{_escape(_enzyme_label(enzyme_id))}</text>"
        )
    cells = []
    for cell in projection.cells:
        row = nick_index[cell.nick_enzyme_id]
        column = action_index[cell.future_release_action_id]
        x = left + column * cell_width
        y = top + row * cell_height
        if cell.status == "proven_minimum":
            overhead = cell.minimum_retained_overhead_nt
            if overhead is None:  # pragma: no cover - typed cell rejects this state
                raise ValueError("A proven matrix cell requires a retained-overhead value.")
            color_index = round(
                overhead * (len(palette) - 1) / max(1, projection.max_retained_overhead_nt)
            )
            fill = palette[color_index]
            value = str(overhead)
        elif cell.status == "infeasible":
            fill = "#e4e7e5"
            value = "—"
        else:
            fill = "url(#unknown-hatch)"
            value = "?"
        cells.append(
            f'<g data-cell-status="{cell.status}" '
            f'data-nick-enzyme-id="{_escape(cell.nick_enzyme_id)}" '
            f'data-release-action-id="{_escape(cell.future_release_action_id)}" '
            f'data-realization-ids="{_escape(" ".join(cell.realization_ids))}">'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_width:.1f}" '
            f'height="{cell_height}" fill="{fill}" stroke="#ffffff" stroke-width="2"/>'
            f'<text x="{x + cell_width / 2:.1f}" y="{y + 28:.1f}" text-anchor="middle" '
            f'class="body">{value}</text></g>'
        )
    height = max(430, top + len(projection.nick_enzyme_ids) * cell_height + 140)
    scale_label = (
        "Cell value: smallest proven local retained overhead, "
        f"0-{projection.max_retained_overhead_nt} nt"
    )
    status_key = (
        "Gray: no local solution after complete coverage · Unknown: declared search ended "
        "before the cell was resolved."
    )
    boundary = (
        "Local accessibility does not establish scaffold completion, route validity, or "
        "physical construction."
    )
    body = (
        _status_header(projection, title)
        + f"""
<defs><pattern id="unknown-hatch" width="8" height="8" patternUnits="userSpaceOnUse"
patternTransform="rotate(45)"><rect width="8" height="8" fill="#ffffff"/>
<line x1="0" y1="0" x2="0" y2="8" stroke="#9aa49f" stroke-width="2"/></pattern></defs>
<text x="72" y="178" class="subtitle">{_escape(scale_label)}</text>
<text x="{left}" y="{top - 50}" class="label">Future Type IIS action</text>
<text x="72" y="{top - 4}" class="label">Basal nickase</text>
{"".join(labels)}
{"".join(cells)}
<text x="72" y="{height - 58}" class="small">{_escape(status_key)}</text>
<text x="72" y="{height - 30}" class="small">{_escape(boundary)}</text>
"""
    )
    return _document(title=title, body=body, height=height)


def _enzyme_label(enzyme_id: str) -> str:
    return enzyme_id.removesuffix("@1").rsplit("/", 1)[-1]


def _render_retained_overhead(projection: RetainedOverheadFrontierProjection) -> bytes:
    first_hit = next(
        (level.retained_overhead_nt for level in projection.levels if level.realization_count),
        None,
    )
    partition = projection.sequence_partition
    scope = _partition_scope(partition)
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
            f'data-failure-reasons="{_escape(failures)}" '
            f'data-realization-ids="{_escape(ids)}">'
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
        _status_header(projection, title)
        + f"""
<text x="72" y="174" class="subtitle">Absolute retained non-payload overhead</text>
<line x1="140" y1="260" x2="1060" y2="260" class="rule"/>
{"".join(levels)}
<text x="72" y="378" class="small">Candidate, accepted, rejected, and primary failure counts
replay the source level accounting; exact realization membership remains in SVG data.</text>
"""
    )
    return _document(title=title, body=body, height=438)


def _feasibility_title(
    family: str,
    completion: SearchCompletionStatus,
    feasibility: SearchFeasibilityStatus,
    count: int,
    partition: SequenceDomainPartition | None,
) -> str:
    lower = family.lower()
    scope = _partition_scope(partition)
    if completion is not SearchCompletionStatus.COMPLETE:
        return (
            f"{family} discovery was {completion.value} with {count} observed exact local route "
            f"realizations{scope}."
        )
    if feasibility is SearchFeasibilityStatus.FEASIBLE:
        noun = "realization" if count == 1 else "realizations"
        return (
            f"{family} discovery identified {count} exact local route {noun} "
            f"under the declared molecular model{scope}."
        )
    if feasibility is SearchFeasibilityStatus.INFEASIBLE:
        if partition is not None:
            return f"No local {lower} route satisfied the declared molecular constraints{scope}."
        return (
            f"No local {lower} route satisfied the declared molecular constraints after "
            "exhaustive search."
        )
    raise ValueError("Complete local search projections must resolve feasibility.")


def _status_header(
    projection: LocalScientificProjection,
    title: str,
) -> str:
    claims = projection.claim_boundary
    partition_attributes = _partition_attributes(projection.sequence_partition)
    coverage = (
        f"Coverage: {projection.disposition.completion.value} · "
        f"feasibility: {projection.disposition.feasibility.value}"
    )
    boundary = (
        "Local feasibility only; complete route composition and physical construction are not "
        "established."
    )
    return f"""
<g data-completion="{projection.disposition.completion.value}"
data-feasibility="{projection.disposition.feasibility.value}"
data-termination-reason="{projection.disposition.termination_reason.value}"
data-endpoint="{projection.endpoint.value}"
data-projection-id="{projection.projection_id}"
data-result-id="{projection.source_result_id}"
data-hop-version="{_escape(projection.provenance.hop_version)}"
data-renderer-version="{_escape(projection.renderer_version)}"{partition_attributes}
data-digital-design="{claims.digital_design.value}"
data-method="{claims.method.value}"
data-physical-construction="{claims.physical_construction.value}"
data-quality-control="{claims.quality_control.value}"
data-biological-activity="{claims.biological_activity.value}">
<text x="72" y="60" class="title">{_escape(title)}</text>
<text x="72" y="98" class="subtitle">{_escape(coverage)}</text>
<text x="72" y="128" class="small">{_escape(boundary)}</text>
</g>
<line x1="72" y1="150" x2="1128" y2="150" class="rule"/>
"""


def _partition_scope(partition: SequenceDomainPartition | None) -> str:
    if partition is None:
        return ""
    return f" in sequence-domain part {partition.part_index + 1} of {partition.part_count}"


def _partition_attributes(partition: SequenceDomainPartition | None) -> str:
    if partition is None:
        return ""
    return (
        f'\ndata-sequence-part-count="{partition.part_count}" '
        f'data-sequence-part-index="{partition.part_index}"'
    )


def _endpoint_label(endpoint: ConstructionEndpoint) -> str:
    return {
        ConstructionEndpoint.SSDNA_HAIRPIN: "single-stranded hairpin endpoint",
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX: "hairpin PCR duplex endpoint",
        ConstructionEndpoint.CLONE_READY_DUPLEX: "clone-ready duplex endpoint",
    }[endpoint]
