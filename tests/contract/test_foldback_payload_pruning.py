"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_foldback_payload_pruning.py

Tests complete exclusion when a fixed payload contains an unintended actionable site.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import pytest

from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.foldback.realization import _realization
from hop_design.design.construction.verification import verify_foldback_neighborhood_result
from hop_design.kernel.construction.foldback import (
    FoldbackPlacementFailure,
    iter_foldback_program_solutions,
    iter_foldback_programs,
)
from hop_design.models.construction import (
    FinalPayloadReference,
    FoldbackTarget,
    SearchCompletionStatus,
    SearchFeasibilityStatus,
    SequenceDomainPartition,
)
from hop_design.models.coordinates import Boundary
from hop_design.models.payload import ExactPayload
from hop_design.models.physical import Strand
from tests.contract.test_foldback_construction_discovery import _nickase, _request, _terminus_enzyme


@pytest.mark.parametrize("strand", [Strand.TOP, Strand.BOTTOM])
@pytest.mark.parametrize("partition_index", [None, 0, 1])
def test_fixed_payload_site_excludes_the_whole_loop_domain_with_one_evaluation(
    strand, partition_index
):
    request = _request(
        _nickase(motif="GAC"),
        target=FoldbackTarget(
            nick_strand=strand,
            junction_offset_nt=0,
            loop_length_nt=5,
            annealing_arm_length_bp=3,
        ),
        max_search_nodes=1,
    ).model_copy(
        update={
            "payload": FinalPayloadReference(
                payload=ExactPayload(sequence="TGACAT"),
                basal_boundary=Boundary(offset=0),
                foldback_boundary=Boundary(offset=6),
            )
        }
    )
    if partition_index is not None:
        request = request.model_copy(
            update={
                "search": request.search.model_copy(
                    update={
                        "sequence_partition": SequenceDomainPartition(
                            part_count=2, part_index=partition_index
                        )
                    }
                )
            }
        )

    result = discover_foldback_neighborhood(request)

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
    assert result.neighborhood.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert result.realizations == ()
    expected_rejections = 0 if partition_index == 1 else 1
    assert result.neighborhood.rejected_count == expected_rejections
    assert [(reason.code, reason.count) for reason in result.neighborhood.failure_reasons] == (
        [("unintended-actionable-site", 1)] if expected_rejections else []
    )
    assert verify_foldback_neighborhood_result(result).result == result


@pytest.mark.parametrize("strand", [Strand.TOP, Strand.BOTTOM])
@pytest.mark.parametrize("payload", ["TGACAT", "TCATGA", "TGGCCA"])
@pytest.mark.parametrize("cut_offset", [0, -2])
def test_payload_pruning_preserves_the_exact_exhaustive_replay_members(strand, payload, cut_offset):
    target = FoldbackTarget(
        nick_strand=strand,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    request = _request(
        _nickase(motif="GAC", cut_offset=cut_offset),
        _terminus_enzyme(),
        target=target,
        max_search_nodes=10000,
        max_realizations=10000,
    ).model_copy(
        update={
            "payload": FinalPayloadReference(
                payload=ExactPayload(sequence=payload),
                basal_boundary=Boundary(offset=0),
                foldback_boundary=Boundary(offset=len(payload)),
            )
        }
    )
    expected = []
    for program in iter_foldback_programs(request.enzyme_provisioning, target=target):
        for solution in iter_foldback_program_solutions(
            payload_sequence=payload, target=target, program=program
        ):
            if isinstance(solution, FoldbackPlacementFailure):
                continue
            record = _realization(
                request=request,
                payload_sequence=payload,
                target=target,
                route=program,
                solution=solution,
            )
            if not isinstance(record, str):
                expected.append(record)

    result = discover_foldback_neighborhood(request)

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
    assert result.realizations == tuple(expected)
    if payload == "TCATGA" and cut_offset == -2:
        assert expected
