"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/local_svg_common.py

Provides shared claim and coverage labels for local construction SVGs.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import SearchCompletionStatus, SearchFeasibilityStatus
from hop_design.models.construction.projections import LocalScientificProjection
from hop_design.models.construction.sequence_domain import SequenceDomainPartition

from .svg_common import escape


def feasibility_title(
    family: str,
    completion: SearchCompletionStatus,
    feasibility: SearchFeasibilityStatus,
    count: int,
    partition: SequenceDomainPartition | None,
) -> str:
    """Describe local-search coverage and feasibility without implying ranking."""
    lower = family.lower()
    scope = partition_scope(partition)
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


def status_header(projection: LocalScientificProjection, title: str) -> str:
    """Render the shared local-search authority and claim boundary."""
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
data-hop-version="{escape(projection.provenance.hop_version)}"
data-renderer-version="{escape(projection.renderer_version)}"{partition_attributes}
data-digital-design="{claims.digital_design.value}"
data-method="{claims.method.value}"
data-physical-construction="{claims.physical_construction.value}"
data-quality-control="{claims.quality_control.value}"
data-biological-activity="{claims.biological_activity.value}">
<text x="72" y="60" class="title">{escape(title)}</text>
<text x="72" y="98" class="subtitle">{escape(coverage)}</text>
<text x="72" y="128" class="small">{escape(boundary)}</text>
</g>
<line x1="72" y1="150" x2="1128" y2="150" class="rule"/>
"""


def partition_scope(partition: SequenceDomainPartition | None) -> str:
    """Describe the explicit sequence-domain partition, when present."""
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
