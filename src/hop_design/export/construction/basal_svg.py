"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/basal_svg.py

Renders basal-neighborhood feasibility and overhead projections as SVG.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import NamedTuple

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalFeasibilityRow,
    BasalMinimumOverheadMatrixProjection,
)

from .local_svg_common import feasibility_title, status_header
from .svg_common import escape, render_document


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


def render_basal_projection_svg(projection: BasalFeasibilityProjection) -> bytes:
    """Render exact basal realization groups and their annealing obligations."""
    endpoint = _endpoint_label(projection.endpoint)
    title = feasibility_title(
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
            f'data-realization-ids="{escape(" ".join(realization_ids))}">'
            f'<text x="72" y="{y}" class="body">{escape(route)}</text>'
            f'<text x="360" y="{y}" class="body">{escape(pairing)}</text>'
            f'<text x="720" y="{y}" class="body">{escape(obligation)}</text>'
            f'<text x="1080" y="{y}" class="body">n={len(realization_ids)}</text></g>'
        )
    body = (
        status_header(projection, title)
        + f"""
<text x="72" y="168" class="subtitle">Requested endpoint: {escape(endpoint)}</text>
<text x="72" y="206" class="label">Local pairing and upstream completion obligations</text>
{"".join(rows)}
<text x="72" y="{max(296, 250 + len(rows) * 38 + 30)}" class="small">
Rows group identical observed dimensions; no preference is inferred.</text>
"""
    )
    return render_document(title=title, body=body, height=max(380, 350 + len(rows) * 38))


def render_basal_matrix_svg(projection: BasalMinimumOverheadMatrixProjection) -> bytes:
    """Render proven overhead minima across nickase and release-action pairs."""
    title = "Basal local accessibility by nickase and future release action"
    left = 300
    top = 286
    matrix_width = 820
    columns_per_block = 4
    columns = min(columns_per_block, len(projection.release_actions))
    cell_width = matrix_width / columns
    cell_height = 44
    block_height = len(projection.nick_enzyme_ids) * cell_height + 104
    actions = sorted(
        projection.release_actions,
        key=lambda action: (
            action.enzyme_id,
            action.requirement.orientation.value,
            action.requirement.product_end,
            action.requirement.overhang_end.value,
            action.requirement.cohesive_end_sequence,
            action.action_id,
        ),
    )
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
    action_index = {action.action_id: index for index, action in enumerate(actions)}
    nick_index = {enzyme_id: index for index, enzyme_id in enumerate(projection.nick_enzyme_ids)}
    labels = []
    for index, action in enumerate(actions):
        block, column = divmod(index, columns_per_block)
        block_top = top + block * block_height
        x = left + column * cell_width + cell_width / 2
        label = f"{_enzyme_label(action.enzyme_id)} · {action.requirement.orientation.value}"
        end = action.requirement.cohesive_end_sequence
        labels.append(
            f'<text x="{x:.1f}" y="{block_top - 42}" text-anchor="middle" class="small">'
            f"{escape(label)}</text>"
            f'<text x="{x:.1f}" y="{block_top - 20}" text-anchor="middle" class="body">'
            f"{escape(end)} · {action.requirement.product_end} end</text>"
        )
    block_count = (len(projection.release_actions) + columns_per_block - 1) // columns_per_block
    for block in range(block_count):
        for index, enzyme_id in enumerate(projection.nick_enzyme_ids):
            y = top + block * block_height + index * cell_height + cell_height / 2 + 5
            labels.append(
                f'<text x="{left - 18}" y="{y:.1f}" text-anchor="end" class="body">'
                f"{escape(_enzyme_label(enzyme_id))}</text>"
            )
    cells = []
    for cell in projection.cells:
        row = nick_index[cell.nick_enzyme_id]
        block, column = divmod(action_index[cell.future_release_action_id], columns_per_block)
        x = left + column * cell_width
        y = top + block * block_height + row * cell_height
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
            f'data-nick-enzyme-id="{escape(cell.nick_enzyme_id)}" '
            f'data-release-action-id="{escape(cell.future_release_action_id)}" '
            f'data-realization-ids="{escape(" ".join(cell.realization_ids))}">'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_width:.1f}" '
            f'height="{cell_height}" fill="{fill}" stroke="#ffffff" stroke-width="2"/>'
            f'<text x="{x + cell_width / 2:.1f}" y="{y + 28:.1f}" text-anchor="middle" '
            f'class="body">{value}</text></g>'
        )
    height = max(430, top + block_count * block_height + 36)
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
        status_header(projection, title)
        + f"""
<defs><pattern id="unknown-hatch" width="8" height="8" patternUnits="userSpaceOnUse"
patternTransform="rotate(45)"><rect width="8" height="8" fill="#ffffff"/>
<line x1="0" y1="0" x2="0" y2="8" stroke="#9aa49f" stroke-width="2"/></pattern></defs>
<text x="72" y="178" class="subtitle">{escape(scale_label)}</text>
<text x="{left}" y="{top - 78}" class="label">
Future Type IIS action and cohesive end (5&#8242; to 3&#8242;)</text>
<text x="72" y="{top - 4}" class="label">Basal nickase</text>
{"".join(labels)}
{"".join(cells)}
<text x="72" y="{height - 58}" class="small">{escape(status_key)}</text>
<text x="72" y="{height - 30}" class="small">{escape(boundary)}</text>
"""
    )
    return render_document(title=title, body=body, height=height)


def _enzyme_label(enzyme_id: str) -> str:
    return enzyme_id.removesuffix("@1").rsplit("/", 1)[-1]


def _endpoint_label(endpoint: ConstructionEndpoint) -> str:
    return {
        ConstructionEndpoint.SSDNA_HAIRPIN: "single-stranded hairpin endpoint",
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX: "hairpin PCR duplex endpoint",
        ConstructionEndpoint.CLONE_READY_DUPLEX: "clone-ready duplex endpoint",
    }[endpoint]
