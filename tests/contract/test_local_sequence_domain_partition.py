"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_local_sequence_domain_partition.py

Tests deterministic partitioning of exact local sequence domains.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import hop_design.construction as construction
from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.models.construction import (
    ConstructionConstraints,
    ConstructionEndpoint,
    FoldbackTarget,
    NeighborhoodDiscoveryResult,
    NeighborhoodSearchPlan,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    SequenceDomainPartition,
    problem_id,
)
from hop_design.models.physical import Strand
from tests.contract.test_basal_construction_discovery import _request as _basal_request
from tests.contract.test_foldback_construction_discovery import _nickase, _request


def _with_partition(request, *, part_count: int, part_index: int):
    return request.model_copy(
        update={
            "search": NeighborhoodSearchPlan(
                max_retained_overhead_nt=request.search.max_retained_overhead_nt,
                max_search_nodes=request.search.max_search_nodes,
                max_realizations=request.search.max_realizations,
                scope=request.search.scope,
                stop=request.search.stop,
                result_quota=request.search.result_quota,
                sequence_partition=SequenceDomainPartition(
                    part_count=part_count,
                    part_index=part_index,
                ),
            )
        }
    )


def _partitioned_request(*, part_count: int, part_index: int):
    return _with_partition(
        _request(
            _nickase(motif="ACANTT"),
            target=None,
            max_search_nodes=100,
            max_realizations=100,
        ),
        part_count=part_count,
        part_index=part_index,
    )


def _realization_ids(result: object) -> tuple[str, ...]:
    return tuple(
        record.local_realization.local_realization_id  # type: ignore[attr-defined]
        for record in result.realizations  # type: ignore[attr-defined]
    )


def test_sequence_domain_partition_rejects_empty_or_out_of_range_parts() -> None:
    with pytest.raises(ValidationError, match="part_count"):
        SequenceDomainPartition(part_count=1, part_index=0)

    with pytest.raises(ValidationError, match="part_index"):
        SequenceDomainPartition(part_count=4, part_index=4)


def test_partition_parts_are_complete_disjoint_and_reconstruct_the_exact_search() -> None:
    unpartitioned_request = _request(
        _nickase(motif="ACANTT"),
        max_search_nodes=100,
        max_realizations=100,
    )
    unpartitioned = discover_foldback_neighborhood(unpartitioned_request)
    parts = tuple(
        discover_foldback_neighborhood(_partitioned_request(part_count=4, part_index=index))
        for index in range(4)
    )

    expected_ids = _realization_ids(unpartitioned)
    part_ids = tuple(_realization_ids(part) for part in parts)

    assert all(part.neighborhood.disposition.completion == "complete" for part in parts)
    assert all(part.neighborhood.payload_compatibility.status == "not_computed" for part in parts)
    assert all(part.neighborhood.problem_id == problem_id(unpartitioned_request) for part in parts)
    assert len({part.neighborhood.execution_id for part in parts}) == 4
    assert all(
        set(left).isdisjoint(right)
        for index, left in enumerate(part_ids)
        for right in part_ids[index + 1 :]
    )
    assert {member for part in part_ids for member in part} == set(expected_ids)
    expected_by_id = {
        record.local_realization.local_realization_id: record.model_dump(mode="json")
        for record in unpartitioned.realizations
    }
    assert all(
        record.model_dump(mode="json")
        == expected_by_id[record.local_realization.local_realization_id]
        for part in parts
        for record in part.realizations
    )
    assert sum(
        level.candidate_count for part in parts for level in part.neighborhood.overhead_levels
    ) == sum(level.candidate_count for level in unpartitioned.neighborhood.overhead_levels)
    assert sum(part.neighborhood.rejected_count for part in parts) == (
        unpartitioned.neighborhood.rejected_count
    )


def test_partition_preserves_both_duplex_nick_orientations() -> None:
    unpartitioned = discover_foldback_neighborhood(
        _request(_nickase(motif="ACANTT"), max_search_nodes=100, max_realizations=100)
    )
    parts = tuple(
        discover_foldback_neighborhood(_partitioned_request(part_count=2, part_index=index))
        for index in range(2)
    )

    assert {
        record.local_realization.achieved_geometry.nick_strand
        for part in parts
        for record in part.realizations
    } == {Strand.TOP, Strand.BOTTOM}
    assert {member for part in parts for member in _realization_ids(part)} == set(
        _realization_ids(unpartitioned)
    )


def test_partition_is_not_allowed_with_all_member_compatibility() -> None:
    request = _partitioned_request(part_count=2, part_index=0)
    with pytest.raises(ValidationError, match="all-member compatibility"):
        type(request).model_validate(
            {
                **request.model_dump(mode="python"),
                "hard_constraints": ConstructionConstraints(require_all_members_compatible=True),
            }
        )


def test_partition_result_cannot_claim_whole_domain_payload_compatibility() -> None:
    result = discover_foldback_neighborhood(_partitioned_request(part_count=2, part_index=0))
    with pytest.raises(ValidationError, match="whole-domain payload compatibility"):
        NeighborhoodDiscoveryResult.model_validate(
            {
                **result.neighborhood.model_dump(mode="python"),
                "payload_compatibility": PayloadCompatibilityAccounting(
                    status=PayloadCompatibilityStatus.COMPLETE,
                    total_assignments=1,
                    compatible_assignments=1,
                    excluded_assignments=0,
                    exhaustive=True,
                ),
            }
        )


def test_partition_can_complete_below_a_bound_that_truncates_the_full_domain() -> None:
    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    request = _request(
        _nickase(motif="ACANTT"),
        target=target,
        max_search_nodes=100,
        max_realizations=2,
    )
    unpartitioned = discover_foldback_neighborhood(request)
    parts = tuple(
        discover_foldback_neighborhood(_with_partition(request, part_count=2, part_index=index))
        for index in range(2)
    )

    assert unpartitioned.neighborhood.disposition.completion == "truncated"
    assert all(part.neighborhood.disposition.completion == "complete" for part in parts)
    assert sum(len(part.realizations) for part in parts) == 4


def test_basal_parts_are_disjoint_and_reconstruct_the_exact_search() -> None:
    request = _basal_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    unpartitioned = discover_basal_neighborhood(request)
    parts = tuple(
        discover_basal_neighborhood(_with_partition(request, part_count=2, part_index=index))
        for index in range(2)
    )
    expected_ids = {
        record.local_realization.local_realization_id for record in unpartitioned.realizations
    }
    part_ids = tuple(
        {record.local_realization.local_realization_id for record in part.realizations}
        for part in parts
    )

    assert part_ids[0].isdisjoint(part_ids[1])
    assert part_ids[0] | part_ids[1] == expected_ids
    assert all(part.discovery.payload_compatibility.status == "not_computed" for part in parts)


def test_public_receipt_persists_and_replays_one_declared_partition(tmp_path: Path) -> None:
    request = _partitioned_request(part_count=4, part_index=3)
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request.model_dump(mode="json", by_alias=True), sort_keys=True))

    receipt = construction.discover_local_neighborhood(source)
    payload = json.loads(receipt.json_bytes)

    assert payload["neighborhood"]["request"]["search"]["sequence_partition"] == {
        "part_count": 4,
        "part_index": 3,
    }
    result = receipt.write(tmp_path / "result")
    loaded = construction.load_verified_local_neighborhood(result / "result.json")
    assert loaded.result_id == receipt.result_id
    assert loaded.json_bytes == receipt.json_bytes
