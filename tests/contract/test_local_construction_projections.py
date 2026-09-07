"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_local_construction_projections.py

Tests neutral, lossless scientific projections of local construction discovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.projections import (
    project_basal_feasibility,
    project_foldback_feasibility,
    project_retained_overhead_frontier,
    verify_local_projection,
)
from hop_design.export.construction import (
    render_projection_csv,
    render_projection_json,
    render_projection_svg,
)
from hop_design.models.construction import (
    ConstructionEndpoint,
    FailureReasonCount,
    FoldbackGeometryDomain,
    NickStrandSelection,
    SearchCompletionStatus,
    SearchDisposition,
    SearchFeasibilityStatus,
    SearchTerminationReason,
    SequenceDomainPartition,
    grouped_realization_projection,
)
from tests.contract.test_basal_construction_discovery import _request as basal_request
from tests.contract.test_foldback_construction_discovery import (
    _nickase as foldback_nickase,
)
from tests.contract.test_foldback_construction_discovery import (
    _request as foldback_request,
)
from tests.contract.test_foldback_construction_discovery import (
    _terminus_enzyme as foldback_terminus_enzyme,
)


def _csv_rows(content: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def _partitioned(request, *, part_count: int = 2, part_index: int = 0):
    return request.model_copy(
        update={
            "search": request.search.model_copy(
                update={
                    "sequence_partition": SequenceDomainPartition(
                        part_count=part_count,
                        part_index=part_index,
                    )
                }
            )
        }
    )


@pytest.mark.parametrize("family", ["foldback", "basal"])
def test_partitioned_local_projections_preserve_declared_scope_in_json_and_csv(
    family: str,
) -> None:
    partition = SequenceDomainPartition(part_count=3, part_index=1)
    if family == "foldback":
        result = discover_foldback_neighborhood(
            _partitioned(
                foldback_request(
                    foldback_nickase(motif="ACANTT"),
                    max_search_nodes=100,
                    max_realizations=100,
                ),
                part_count=partition.part_count,
                part_index=partition.part_index,
            )
        )
        feasibility = project_foldback_feasibility(result)
    else:
        result = discover_basal_neighborhood(
            _partitioned(
                basal_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX),
                part_count=partition.part_count,
                part_index=partition.part_index,
            )
        )
        feasibility = project_basal_feasibility(result)
    overhead = project_retained_overhead_frontier(result)

    for projection in (feasibility, overhead):
        assert projection.sequence_partition == partition
        rendered = json.loads(render_projection_json(projection))
        assert rendered["sequence_partition"] == {"part_count": 3, "part_index": 1}
        rows = _csv_rows(render_projection_csv(projection))
        assert rows
        assert {row["sequence_part_count"] for row in rows} == {"3"}
        assert {row["sequence_part_index"] for row in rows} == {"1"}
    expected_schemas = {
        "foldback": (
            "hop.foldback-feasibility-landscape/v4",
            "hop.foldback-overhead-frontier/v2",
        ),
        "basal": (
            "hop.basal-feasibility-landscape/v5",
            "hop.basal-overhead-frontier/v2",
        ),
    }
    assert (feasibility.schema_id, overhead.schema_id) == expected_schemas[family]
    mismatched = feasibility.model_dump(mode="python", by_alias=True)
    mismatched["schema"] = {
        "foldback": "hop.foldback-feasibility-landscape/v3",
        "basal": "hop.basal-feasibility-landscape/v4",
    }[family]
    with pytest.raises(ValidationError, match="sequence-domain scope"):
        type(feasibility).model_validate(mismatched)


def test_infeasible_partition_svg_cannot_claim_exhaustive_whole_domain_search() -> None:
    result = discover_foldback_neighborhood(
        _partitioned(
            foldback_request(foldback_nickase(motif="GACA", cut_offset=4)),
            part_count=4,
            part_index=2,
        )
    )
    assert result.neighborhood.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE

    for projection in (
        project_foldback_feasibility(result),
        project_retained_overhead_frontier(result),
    ):
        svg = render_projection_svg(projection).decode("utf-8")
        assert "sequence-domain part 3 of 4" in svg
        assert 'data-sequence-part-count="4"' in svg
        assert 'data-sequence-part-index="2"' in svg
        assert "exhaustive search" not in svg
        assert "complete overhead envelope" not in svg


def test_foldback_projection_preserves_exact_membership_and_truthful_status() -> None:
    result = discover_foldback_neighborhood(
        foldback_request(foldback_nickase(), foldback_terminus_enzyme())
    )

    projection = project_foldback_feasibility(result)

    assert projection.disposition.completion is SearchCompletionStatus.COMPLETE
    assert projection.disposition.feasibility is SearchFeasibilityStatus.FEASIBLE
    assert projection.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
    assert projection.source_result_id == result.result_id
    assert projection.projection_reference.result_id == result.result_id
    assert projection.schema_id == "hop.foldback-feasibility-landscape/v3"
    assert projection.projection_reference.renderer_version == "foldback-feasibility-projections/3"
    assert projection.provenance == result.neighborhood.provenance
    assert projection.claim_boundary == result.neighborhood.claim_boundary
    assert (
        projection.projection_id
        == grouped_realization_projection(
            result_id=result.result_id,
            projection_schema=projection.schema_id,
            renderer_version="foldback-feasibility-projections/3",
            realization_ids=tuple(
                item.local_realization.local_realization_id for item in result.realizations
            ),
            groups=result.neighborhood.achieved_geometry_groups,
        ).projection_id
    )
    assert projection.realization_count == len(result.realizations)
    assert tuple(row.local_realization_id for row in projection.realizations) == tuple(
        item.local_realization.local_realization_id for item in result.realizations
    )
    assert tuple(row.foldback_realization_id for row in projection.realizations) == tuple(
        item.foldback_realization_id for item in result.realizations
    )
    assert tuple(row.nick_strand for row in projection.realizations) == tuple(
        item.foldback_nick.strand for item in result.realizations
    )
    assert tuple(row.source_orientation for row in projection.realizations) == tuple(
        item.payload_source_map.segments[0].orientation for item in result.realizations
    )
    assert {row.program_kind for row in projection.realizations} == {
        "single_cleavage",
        "sequential_terminus_plus_nick",
    }

    csv_rows = _csv_rows(render_projection_csv(projection))
    assert [row["local_realization_id"] for row in csv_rows] == [
        row.local_realization_id for row in projection.realizations
    ]
    assert all(row["completion"] == "complete" for row in csv_rows)
    assert all(row["feasibility"] == "feasible" for row in csv_rows)
    assert [row["nick_strand"] for row in csv_rows] == [
        item.foldback_nick.strand.value for item in result.realizations
    ]
    assert [row["source_orientation"] for row in csv_rows] == [
        item.payload_source_map.segments[0].orientation.value for item in result.realizations
    ]
    rendered_json = json.loads(render_projection_json(projection))
    assert "sequence_partition" not in rendered_json
    assert "sequence_part_count" not in csv_rows[0]
    assert "sequence_part_index" not in csv_rows[0]

    svg = render_projection_svg(projection).decode("utf-8")
    assert (
        f"Foldback discovery identified {len(result.realizations)} exact local route realizations "
        "under the declared molecular model."
    ) in svg
    assert "complete route composition and" in svg
    assert "physical construction are not established" in svg
    assert 'data-completion="complete"' in svg
    assert 'data-feasibility="feasible"' in svg
    assert "Exact realizations satisfying declared constraints" in svg
    assert "Exact compatible realizations" not in svg
    assert "data-sequence-part" not in svg
    assert "data-local-realization-id" not in svg
    assert "data-realization-ids" in svg
    assert "top strand · forward source" in svg
    assert "bottom strand · reverse-complement source" in svg
    assert "rank" not in svg.lower()

    legacy = projection.model_dump(mode="python", by_alias=True)
    legacy["schema"] = "hop.foldback-feasibility-landscape/v2"
    with pytest.raises(ValidationError, match=r"hop\.foldback-feasibility-landscape/v3"):
        type(projection).model_validate(legacy)


def test_basal_projection_keeps_local_pairing_and_completion_obligations() -> None:
    result = discover_basal_neighborhood(basal_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))

    projection = project_basal_feasibility(result)

    assert projection.disposition.completion is SearchCompletionStatus.COMPLETE
    assert projection.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX
    assert projection.schema_id == "hop.basal-feasibility-landscape/v4"
    assert projection.source_result_id == result.result_id
    assert projection.projection_reference.result_id == result.result_id
    assert projection.projection_reference.renderer_version == "basal-projections/4"
    assert projection.provenance == result.discovery.provenance
    assert projection.claim_boundary == result.discovery.claim_boundary
    assert tuple(row.basal_realization_id for row in projection.realizations) == tuple(
        item.basal_realization_id for item in result.realizations
    )
    assert all(row.pairing_pattern is not None for row in projection.realizations)
    assert all(row.proximal_annealing_nt == 4 for row in projection.realizations)
    assert all(row.required_annealing_nt == 15 for row in projection.realizations)
    assert all(row.annealing_completion_nt == 11 for row in projection.realizations)
    assert all(row.future_release_action_id is None for row in projection.realizations)
    for row, source in zip(projection.realizations, result.realizations, strict=True):
        achieved = source.local_realization.achieved_geometry
        assert row.nick_strand == achieved.nick_strand
        assert row.nick_offset_nt == achieved.nick_offset_nt
        assert row.literal_pairs == source.projection.pairing_state.pairs

    csv_row = _csv_rows(render_projection_csv(projection))[0]
    assert csv_row["nick_strand"] == projection.realizations[0].nick_strand.value
    assert json.loads(csv_row["literal_pairs_json"]) == [
        item.model_dump(mode="json") for item in projection.realizations[0].literal_pairs
    ]
    assert csv_row["physical_construction"] == "not_recorded"
    assert csv_row["required_annealing_nt"] == "15"
    assert "sequence_part_count" not in csv_row
    assert "sequence_part_index" not in csv_row

    frontier = project_retained_overhead_frontier(result)
    assert frontier.source_result_id == result.result_id
    assert frontier.schema_id == "hop.basal-overhead-frontier/v1"
    assert tuple(
        (
            level.status,
            level.candidate_count,
            level.realization_count,
            level.rejected_count,
            level.failure_reasons,
        )
        for level in frontier.levels
    ) == tuple(
        (
            "complete" if level.complete else "partial",
            level.candidate_count,
            len(level.realization_ids),
            level.rejected_count,
            level.failure_reasons,
        )
        for level in result.discovery.overhead_levels
    )

    content = projection.model_dump(by_alias=True)
    content["source_result_id"] = f"hop:basal-neighborhood-result/{'0' * 64}@1"
    with pytest.raises(ValidationError, match="replay the shared projection reference"):
        type(projection).model_validate(content)

    svg = render_projection_svg(projection).decode("utf-8")
    assert "hairpin PCR duplex endpoint" in svg
    assert 'data-endpoint="hairpin_pcr_duplex"' in svg
    assert f'data-result-id="{result.result_id}"' in svg
    assert 'data-renderer-version="basal-projections/4"' in svg
    assert 'data-physical-construction="not_recorded"' in svg
    assert "data-sequence-part" not in svg
    assert "top strand · offset" in svg
    assert "Local pairing and upstream completion obligations" in svg
    assert "11 nt completion" in svg
    assert "literal pair patterns" in svg
    assert "data-local-realization-id" not in svg
    assert "data-realization-ids" in svg
    assert "performance" not in svg.lower()


def test_overhead_frontier_preserves_empty_levels_and_exact_membership() -> None:
    domain = FoldbackGeometryDomain(
        nick_strand=NickStrandSelection.ANY,
        junction_offsets_nt=(0,),
        loop_lengths_nt=(3,),
        annealing_arm_lengths_bp=(3, 4),
    )
    result = discover_foldback_neighborhood(
        foldback_request(
            foldback_nickase(motif="GACATTT"),
            domain=domain,
            max_retained_overhead_nt=11,
        )
    )

    projection = project_retained_overhead_frontier(result)

    assert projection.disposition.completion is SearchCompletionStatus.COMPLETE
    assert projection.source_result_id == result.result_id
    assert projection.provenance == result.neighborhood.provenance
    assert projection.claim_boundary == result.neighborhood.claim_boundary
    assert tuple(level.retained_overhead_nt for level in projection.levels) == tuple(range(12))
    assert all(level.realization_count == 0 for level in projection.levels[:11])
    assert projection.levels[11].realization_count == 2
    assert all(level.status == "complete" for level in projection.levels)
    assert tuple(level.candidate_count for level in projection.levels) == tuple(
        level.candidate_count for level in result.neighborhood.overhead_levels
    )
    assert tuple(level.rejected_count for level in projection.levels) == tuple(
        level.rejected_count for level in result.neighborhood.overhead_levels
    )
    assert tuple(level.failure_reasons for level in projection.levels) == tuple(
        level.failure_reasons for level in result.neighborhood.overhead_levels
    )
    assert projection.levels[0].realization_ids == ()
    assert projection.levels[11].realization_ids == tuple(
        item.local_realization.local_realization_id for item in result.realizations
    )

    rows = _csv_rows(render_projection_csv(projection))
    assert rows[0]["retained_overhead_nt"] == "0"
    assert rows[0]["level_status"] == "complete"
    assert int(rows[0]["candidate_count"]) == projection.levels[0].candidate_count
    assert int(rows[0]["rejected_count"]) == projection.levels[0].rejected_count
    assert json.loads(rows[0]["failure_reasons_json"]) == [
        item.model_dump(mode="json") for item in projection.levels[0].failure_reasons
    ]
    assert rows[0]["local_realization_id"] == ""
    assert rows[-2]["retained_overhead_nt"] == "11"
    assert rows[-2]["local_realization_id"] == projection.levels[11].realization_ids[0]

    svg = render_projection_svg(projection).decode("utf-8")
    assert "Feasibility first appeared at 11 retained nucleotides." in svg
    assert 'data-realization-count="0"' in svg
    assert 'data-realization-count="2"' in svg
    assert 'data-level-status="complete"' in svg
    assert "candidates" in svg and "rejected" in svg


def test_overhead_frontier_preserves_partial_and_zero_result_level_accounting() -> None:
    truncated = discover_foldback_neighborhood(
        foldback_request(
            foldback_nickase(),
            foldback_terminus_enzyme(),
            max_search_nodes=1,
        )
    )
    infeasible = discover_foldback_neighborhood(
        foldback_request(foldback_nickase(motif="GACA", cut_offset=4))
    )

    partial = project_retained_overhead_frontier(truncated)
    zero_result = project_retained_overhead_frontier(infeasible)

    assert partial.levels[-1].status == "partial"
    assert (
        partial.levels[-1].candidate_count
        == truncated.neighborhood.overhead_levels[-1].candidate_count
    )
    assert (
        partial.levels[-1].rejected_count
        == truncated.neighborhood.overhead_levels[-1].rejected_count
    )
    assert (
        partial.levels[-1].failure_reasons
        == truncated.neighborhood.overhead_levels[-1].failure_reasons
    )
    assert zero_result.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert all(level.realization_count == 0 for level in zero_result.levels)
    assert sum(level.rejected_count for level in zero_result.levels) > 0
    assert all(level.status == "complete" for level in zero_result.levels)

    zero_rows = _csv_rows(render_projection_csv(zero_result))
    assert zero_rows[0]["local_realization_id"] == ""
    evaluated_row = next(row for row in zero_rows if int(row["candidate_count"]) > 0)
    assert int(evaluated_row["rejected_count"]) > 0
    partial_svg = render_projection_svg(partial).decode("utf-8")
    assert 'data-level-status="partial"' in partial_svg
    assert "partial level" in partial_svg

    rendered = json.loads(render_projection_json(partial))
    assert rendered["levels"][-1]["status"] == "partial"
    assert rendered["levels"][-1]["candidate_count"] == partial.levels[-1].candidate_count
    assert rendered["levels"][-1]["failure_reasons"] == [
        item.model_dump(mode="json") for item in partial.levels[-1].failure_reasons
    ]

    source_level = partial.levels[-1]
    altered_level = source_level.model_copy(
        update={
            "candidate_count": source_level.candidate_count + 1,
            "rejected_count": source_level.rejected_count + 1,
            "failure_reasons": (
                *source_level.failure_reasons,
                FailureReasonCount(code="projection-only-rejection", count=1),
            ),
        }
    )
    content = partial.model_dump(by_alias=True)
    content["levels"] = (*partial.levels[:-1], altered_level)
    resealed = type(partial).model_validate(content)
    with pytest.raises(ValueError, match="does not replay its detailed source result"):
        verify_local_projection(resealed, truncated)

    invalid_completion = partial.model_dump(by_alias=True)
    invalid_completion["disposition"] = SearchDisposition(
        completion=SearchCompletionStatus.COMPLETE,
        feasibility=SearchFeasibilityStatus.FEASIBLE,
        termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
    )
    with pytest.raises(ValidationError, match="partial level"):
        type(partial).model_validate(invalid_completion)


def test_infeasible_and_truncated_projections_do_not_overstate_completion() -> None:
    infeasible = discover_foldback_neighborhood(
        foldback_request(foldback_nickase(motif="GACA", cut_offset=4))
    )
    truncated = discover_foldback_neighborhood(
        foldback_request(
            foldback_nickase(),
            foldback_terminus_enzyme(),
            max_search_nodes=1,
        )
    )

    infeasible_projection = project_foldback_feasibility(infeasible)
    truncated_projection = project_foldback_feasibility(truncated)

    assert infeasible_projection.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert infeasible_projection.realization_count == 0
    assert truncated_projection.disposition.completion is SearchCompletionStatus.TRUNCATED
    assert (
        truncated_projection.disposition.termination_reason
        is SearchTerminationReason.EVALUATION_CAP
    )

    infeasible_svg = render_projection_svg(infeasible_projection).decode("utf-8")
    truncated_svg = render_projection_svg(truncated_projection).decode("utf-8")
    assert (
        "No local foldback route satisfied the declared molecular constraints after "
        "exhaustive search."
    ) in infeasible_svg
    assert "compatible local" not in infeasible_svg
    assert "Foldback discovery was truncated" in truncated_svg
    assert 'data-completion="truncated"' in truncated_svg
    assert "identified after exhaustive search" not in truncated_svg


def test_renderers_depend_only_on_typed_projection_models() -> None:
    import hop_design.export.construction.csv as csv_renderer
    import hop_design.export.construction.json as json_renderer
    import hop_design.export.construction.svg as svg_renderer

    for module in (csv_renderer, json_renderer, svg_renderer):
        source = Path(module.__file__).read_text()
        assert "hop_design.design" not in source
        assert "hop_design.kernel" not in source


def test_source_bound_verification_rejects_resealed_membership_drift() -> None:
    result = discover_foldback_neighborhood(
        foldback_request(foldback_nickase(), foldback_terminus_enzyme())
    )
    projection = project_foldback_feasibility(result)

    assert verify_local_projection(projection, result) is projection

    source_rows = projection.realizations
    fake_row = source_rows[0].model_copy(
        update={
            "local_realization_id": f"hop:local-realization/{'f' * 64}@1",
            "foldback_realization_id": f"hop:foldback-realization/{'e' * 64}@1",
        }
    )
    for rows in (source_rows[:1], tuple(reversed(source_rows)), (*source_rows, fake_row)):
        realization_ids = tuple(row.local_realization_id for row in rows)
        groups = (
            projection.projection_reference.groups[0].model_copy(
                update={
                    "realization_ids": realization_ids,
                    "multiplicity": len(realization_ids),
                }
            ),
        )
        reference = grouped_realization_projection(
            result_id=result.result_id,
            projection_schema=projection.schema_id,
            renderer_version=projection.renderer_version,
            realization_ids=realization_ids,
            groups=groups,
        )
        content = projection.model_dump(by_alias=True)
        content.update(
            projection_reference=reference,
            projection_id=reference.projection_id,
            realization_count=len(rows),
            realizations=rows,
        )
        resealed = type(projection).model_validate(content)
        with pytest.raises(ValueError, match="does not replay its detailed source result"):
            verify_local_projection(resealed, result)
