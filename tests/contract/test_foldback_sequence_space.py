"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_foldback_sequence_space.py

Tests exhaustive exact sequence realization within one foldback geometry.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.kernel.construction.foldback import (
    iter_foldback_program_solutions,
    iter_foldback_programs,
)
from hop_design.models.construction import FoldbackTarget, SearchCompletionStatus
from hop_design.models.physical import Strand
from tests.contract.test_foldback_construction_discovery import _nickase, _request


def test_unconstrained_loop_bases_are_enumerated_without_a_sequence_preference() -> None:
    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        nick_offset_within_foldback_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    request = _request(_nickase(motif="ACANNN"), target=target)
    route = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]

    solutions = tuple(
        iter_foldback_program_solutions(
            payload_sequence="GACA",
            target=request.target,
            program=route,
        )
    )

    assert len(solutions) == 64
    assert tuple(solution.loop_sequence for solution in solutions) == tuple(
        "".join((a, b, c)) for a in "ACGT" for b in "ACGT" for c in "ACGT"
    )
    assert {solution.loop_sequence for solution in solutions} == {
        "".join((a, b, c)) for a in "ACGT" for b in "ACGT" for c in "ACGT"
    }
    assert {solution.foldback_arm_sequence for solution in solutions} == {"TGT"}


def test_internal_nick_enumerates_the_foldback_base_retained_on_the_top_strand() -> None:
    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        nick_offset_within_foldback_nt=1,
        loop_length_nt=4,
        annealing_arm_length_bp=2,
    )
    request = _request(_nickase(motif="ATTTTT"), target=target)
    route = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]

    solutions = tuple(
        iter_foldback_program_solutions(
            payload_sequence="GACA",
            target=target,
            program=route,
        )
    )

    assert tuple(solution.source_reference_sequence for solution in solutions) == tuple(
        "GACA" + retained_base + "ATTTTT" for retained_base in "ACGT"
    )
    assert tuple(solution.retained_sequence for solution in solutions) == tuple(
        "GACA" + retained_base + "AAAAA" + "T" + complement + "TGTC"
        for retained_base, complement in zip("ACGT", "TGCA", strict=True)
    )


def test_discovery_preserves_all_exact_loop_realizations_beneath_one_geometry() -> None:
    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        nick_offset_within_foldback_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    result = discover_foldback_neighborhood(_request(_nickase(motif="ACANTT"), target=target))

    assert result.neighborhood.status is SearchCompletionStatus.COMPLETE
    assert tuple(item.loop_sequence for item in result.realizations) == (
        "AAA",
        "AAC",
        "AAG",
        "AAT",
    )
    assert result.neighborhood.achieved_geometry_groups[0].multiplicity == 4


def test_loop_sequence_enumeration_reports_truncation_instead_of_a_partial_complete_set() -> None:
    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        nick_offset_within_foldback_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    result = discover_foldback_neighborhood(
        _request(_nickase(motif="ACANTT"), target=target, max_search_nodes=2)
    )

    assert result.neighborhood.status is SearchCompletionStatus.TRUNCATED
    assert result.neighborhood.truncation_reasons == ("max_search_nodes",)
    assert tuple(item.loop_sequence for item in result.realizations) == ("AAA", "AAC")
