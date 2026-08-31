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
    project_relaxation_frontier,
    verify_local_projection,
)
from hop_design.export.construction import (
    render_projection_csv,
    render_projection_json,
    render_projection_svg,
)
from hop_design.models.construction import (
    ConstructionEndpoint,
    EnumerationPolicy,
    FailureReasonCount,
    RelaxationCoordinate,
    RelaxationMode,
    RelaxationPolicy,
    SearchCompletionStatus,
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
            "enumeration": EnumerationPolicy(
                max_search_nodes=request.enumeration.max_search_nodes,
                max_realizations=request.enumeration.max_realizations,
                sequence_partition=SequenceDomainPartition(
                    part_count=part_count,
                    part_index=part_index,
                ),
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
    relaxation = project_relaxation_frontier(result)

    for projection in (feasibility, relaxation):
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
            "hop.foldback-relaxation-frontier/v3",
        ),
        "basal": (
            "hop.basal-feasibility-landscape/v3",
            "hop.basal-relaxation-frontier/v2",
        ),
    }
    assert (feasibility.schema_id, relaxation.schema_id) == expected_schemas[family]
    mismatched = feasibility.model_dump(mode="python", by_alias=True)
    mismatched["schema"] = {
        "foldback": "hop.foldback-feasibility-landscape/v3",
        "basal": "hop.basal-feasibility-landscape/v2",
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
    assert result.neighborhood.status is SearchCompletionStatus.INFEASIBLE

    for projection in (
        project_foldback_feasibility(result),
        project_relaxation_frontier(result),
    ):
        svg = render_projection_svg(projection).decode("utf-8")
        assert "sequence-domain part 3 of 4" in svg
        assert 'data-sequence-part-count="4"' in svg
        assert 'data-sequence-part-index="2"' in svg
        assert "exhaustive search" not in svg
        assert "complete relaxation frontier" not in svg


def test_foldback_projection_preserves_exact_membership_and_truthful_status() -> None:
    result = discover_foldback_neighborhood(
        foldback_request(foldback_nickase(), foldback_terminus_enzyme())
    )

    projection = project_foldback_feasibility(result)

    assert projection.status is SearchCompletionStatus.COMPLETE
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
    assert all(row["status"] == "complete" for row in csv_rows)
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
    assert 'data-status="complete"' in svg
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


def test_basal_projection_keeps_endpoint_and_material_dimensions() -> None:
    result = discover_basal_neighborhood(basal_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))

    projection = project_basal_feasibility(result)

    assert projection.status is SearchCompletionStatus.COMPLETE
    assert projection.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX
    assert projection.schema_id == "hop.basal-feasibility-landscape/v2"
    assert projection.source_result_id == result.result_id
    assert projection.projection_reference.result_id == result.result_id
    assert projection.projection_reference.renderer_version == "basal-projections/2"
    assert projection.provenance == result.discovery.provenance
    assert projection.claim_boundary == result.discovery.claim_boundary
    assert tuple(row.basal_realization_id for row in projection.realizations) == tuple(
        item.basal_realization_id for item in result.realizations
    )
    assert all(row.pairing_profile is not None for row in projection.realizations)
    assert all(row.retained_nt >= 0 for row in projection.realizations)
    assert all(row.transient_nt >= 0 for row in projection.realizations)
    assert all(row.auxiliary_nt >= 0 for row in projection.realizations)
    for row, source in zip(projection.realizations, result.realizations, strict=True):
        achieved = source.local_realization.achieved_geometry
        assert row.nick_strand == achieved.nick_strand
        assert row.nick_offset_nt == achieved.nick_offset_nt
        assert row.literal_pairs == source.projection.pairing_profile.pairs

    csv_row = _csv_rows(render_projection_csv(projection))[0]
    assert csv_row["nick_strand"] == projection.realizations[0].nick_strand.value
    assert json.loads(csv_row["literal_pairs_json"]) == [
        item.model_dump(mode="json") for item in projection.realizations[0].literal_pairs
    ]
    assert csv_row["physical_construction"] == "not_recorded"
    assert "sequence_part_count" not in csv_row
    assert "sequence_part_index" not in csv_row

    frontier = project_relaxation_frontier(result)
    assert frontier.source_result_id == result.result_id
    assert frontier.schema_id == "hop.basal-relaxation-frontier/v1"
    assert tuple(
        (
            shell.status,
            shell.candidate_count,
            shell.realization_count,
            shell.rejected_count,
            shell.failure_reasons,
        )
        for shell in frontier.shells
    ) == tuple(
        (
            "complete" if shell.complete else "partial",
            shell.candidate_count,
            len(shell.realization_ids),
            shell.rejected_count,
            shell.failure_reasons,
        )
        for shell in result.discovery.shells
    )

    content = projection.model_dump(by_alias=True)
    content["source_result_id"] = f"hop:basal-neighborhood-result/{'0' * 64}@1"
    with pytest.raises(ValidationError, match="replay the shared projection reference"):
        type(projection).model_validate(content)

    svg = render_projection_svg(projection).decode("utf-8")
    assert "hairpin PCR duplex endpoint" in svg
    assert 'data-endpoint="hairpin_pcr_duplex"' in svg
    assert f'data-result-id="{result.result_id}"' in svg
    assert 'data-renderer-version="basal-projections/2"' in svg
    assert 'data-physical-construction="not_recorded"' in svg
    assert "data-sequence-part" not in svg
    assert "top strand · offset" in svg
    assert "Pairing and exact material accounting" in svg
    assert "literal pair patterns" in svg
    assert "data-local-realization-id" not in svg
    assert "data-realization-ids" in svg
    assert "performance" not in svg.lower()


def test_relaxation_frontier_preserves_empty_shells_and_exact_membership() -> None:
    relaxation = RelaxationPolicy(
        mode=RelaxationMode.FIRST_FEASIBLE_SHELL,
        max_radius=1,
        coordinates=(
            RelaxationCoordinate(
                name="annealing_arm_length_bp",
                minimum=3,
                maximum=4,
            ),
        ),
    )
    result = discover_foldback_neighborhood(
        foldback_request(
            foldback_nickase(motif="GACATTT"),
            relaxation=relaxation,
        )
    )

    projection = project_relaxation_frontier(result)

    assert projection.status is SearchCompletionStatus.COMPLETE
    assert projection.source_result_id == result.result_id
    assert projection.provenance == result.neighborhood.provenance
    assert projection.claim_boundary == result.neighborhood.claim_boundary
    assert projection.coordinate_names == ("annealing_arm_length_bp",)
    assert [(shell.radius, shell.realization_count) for shell in projection.shells] == [
        (0, 0),
        (1, 2),
    ]
    assert tuple(shell.status for shell in projection.shells) == ("complete", "complete")
    assert tuple(shell.candidate_count for shell in projection.shells) == tuple(
        shell.candidate_count for shell in result.neighborhood.shells
    )
    assert tuple(shell.rejected_count for shell in projection.shells) == tuple(
        shell.rejected_count for shell in result.neighborhood.shells
    )
    assert tuple(shell.failure_reasons for shell in projection.shells) == tuple(
        shell.failure_reasons for shell in result.neighborhood.shells
    )
    assert projection.shells[0].realization_ids == ()
    assert projection.shells[1].realization_ids == tuple(
        item.local_realization.local_realization_id for item in result.realizations
    )

    rows = _csv_rows(render_projection_csv(projection))
    assert rows[0]["radius"] == "0"
    assert rows[0]["shell_status"] == "complete"
    assert int(rows[0]["candidate_count"]) == projection.shells[0].candidate_count
    assert int(rows[0]["rejected_count"]) == projection.shells[0].rejected_count
    assert json.loads(rows[0]["failure_reasons_json"]) == [
        item.model_dump(mode="json") for item in projection.shells[0].failure_reasons
    ]
    assert rows[0]["local_realization_id"] == ""
    assert rows[1]["radius"] == "1"
    assert rows[1]["local_realization_id"] == projection.shells[1].realization_ids[0]

    svg = render_projection_svg(projection).decode("utf-8")
    assert "Feasibility first appeared one step from the requested geometry." in svg
    assert 'data-realization-count="0"' in svg
    assert 'data-realization-count="2"' in svg
    assert 'data-shell-status="complete"' in svg
    assert "candidates" in svg and "rejected" in svg


def test_relaxation_frontier_preserves_partial_and_zero_result_shell_accounting() -> None:
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

    partial = project_relaxation_frontier(truncated)
    zero_result = project_relaxation_frontier(infeasible)

    assert partial.shells[-1].status == "partial"
    assert partial.shells[-1].candidate_count == truncated.neighborhood.shells[-1].candidate_count
    assert partial.shells[-1].rejected_count == truncated.neighborhood.shells[-1].rejected_count
    assert partial.shells[-1].failure_reasons == truncated.neighborhood.shells[-1].failure_reasons
    assert zero_result.status is SearchCompletionStatus.INFEASIBLE
    assert all(shell.realization_count == 0 for shell in zero_result.shells)
    assert sum(shell.rejected_count for shell in zero_result.shells) > 0
    assert all(shell.status == "complete" for shell in zero_result.shells)

    zero_rows = _csv_rows(render_projection_csv(zero_result))
    assert zero_rows[0]["local_realization_id"] == ""
    assert int(zero_rows[0]["candidate_count"]) > 0
    assert int(zero_rows[0]["rejected_count"]) > 0
    partial_svg = render_projection_svg(partial).decode("utf-8")
    assert 'data-shell-status="partial"' in partial_svg
    assert "partial shell" in partial_svg

    rendered = json.loads(render_projection_json(partial))
    assert rendered["shells"][-1]["status"] == "partial"
    assert rendered["shells"][-1]["candidate_count"] == partial.shells[-1].candidate_count
    assert rendered["shells"][-1]["failure_reasons"] == [
        item.model_dump(mode="json") for item in partial.shells[-1].failure_reasons
    ]

    source_shell = partial.shells[-1]
    altered_shell = source_shell.model_copy(
        update={
            "candidate_count": source_shell.candidate_count + 1,
            "rejected_count": source_shell.rejected_count + 1,
            "failure_reasons": (
                *source_shell.failure_reasons,
                FailureReasonCount(code="projection-only-rejection", count=1),
            ),
        }
    )
    content = partial.model_dump(by_alias=True)
    content["shells"] = (*partial.shells[:-1], altered_shell)
    resealed = type(partial).model_validate(content)
    with pytest.raises(ValueError, match="does not replay its detailed source result"):
        verify_local_projection(resealed, truncated)

    invalid_completion = partial.model_dump(by_alias=True)
    invalid_completion.update(
        status=SearchCompletionStatus.COMPLETE,
        truncation_reasons=(),
    )
    with pytest.raises(ValidationError, match="Only a truncated frontier"):
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

    assert infeasible_projection.status is SearchCompletionStatus.INFEASIBLE
    assert infeasible_projection.realization_count == 0
    assert truncated_projection.status is SearchCompletionStatus.TRUNCATED
    assert truncated_projection.truncation_reasons == ("max_search_nodes",)

    infeasible_svg = render_projection_svg(infeasible_projection).decode("utf-8")
    truncated_svg = render_projection_svg(truncated_projection).decode("utf-8")
    assert (
        "No local foldback route satisfied the declared molecular constraints after "
        "exhaustive search."
    ) in infeasible_svg
    assert "compatible local" not in infeasible_svg
    assert "Foldback discovery was truncated" in truncated_svg
    assert 'data-status="truncated"' in truncated_svg
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
