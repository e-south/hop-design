"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_foldback_sequence_space.py

Tests exhaustive exact sequence realization within one foldback geometry.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import pytest

from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.kernel.construction.foldback import (
    iter_foldback_program_solutions,
    iter_foldback_programs,
)
from hop_design.models.construction import (
    FoldbackTarget,
    SearchCompletionStatus,
    SearchTerminationReason,
)
from hop_design.models.physical import Strand
from tests.contract.test_foldback_construction_discovery import _nickase, _request


@pytest.mark.parametrize("strand", (Strand.TOP, Strand.BOTTOM))
def test_foldback_domain_excludes_nick_recognition_removed_by_terminus_cleavage(strand):
    from hop_design.kernel.construction.foldback.domains import solve_foldback_sequence_domain
    from hop_design.models.construction.foldback import FoldbackCleavageProgramKind
    from hop_design.models.enzymes import RecognitionOrientationSemantics
    from tests.contract.test_foldback_construction_discovery import _terminus_enzyme

    target = FoldbackTarget(
        nick_strand=strand,
        junction_offset_nt=3,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    request = _request(
        _nickase(motif="ACANNN"),
        _terminus_enzyme(
            motif="AAGC",
            orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        ),
        target=target,
    )
    programs = tuple(
        program
        for program in iter_foldback_programs(request.enzyme_provisioning, target=target)
        if program.kind is FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK
    )
    outcomes = tuple(
        solve_foldback_sequence_domain(payload_sequence="GACA", target=target, program=program)
        for program in programs
    )
    assert outcomes
    assert all(
        outcome.code == "foldback-nick-site-exceeds-terminated-substrate" for outcome in outcomes
    )


@pytest.mark.parametrize(
    ("strand", "source"),
    ((Strand.TOP, "GACAACAACTTGT"), (Strand.BOTTOM, "ACAAGTTGTTGTC")),
)
def test_foldback_domain_recovers_correlated_sources_from_independent_bases(strand, source):
    from hop_design.kernel.construction.foldback.domains import solve_foldback_sequence_domain

    target = FoldbackTarget(
        nick_strand=strand,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    request = _request(_nickase(motif="ACANNN"), target=target)
    program = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]

    domain = solve_foldback_sequence_domain(payload_sequence="GACA", target=target, program=program)

    assert domain.independent_domains == (("A",), ("C",), ("A",), *(tuple("ACGT"),) * 3)
    assert domain.cardinality == 64
    solution = domain.materialize("ACAAGT")
    assert solution.source_reference_sequence == source
    assert solution.retained_sequence == "GACAACAAGTTGTTGTC"
    assert solution.loop_sequence == "AGT"
    assert solution.foldback_arm_sequence == "TGT"
    with pytest.raises(ValueError, match="domain"):
        domain.materialize("ACCAGT")
    with pytest.raises(ValueError, match="length"):
        domain.materialize("ACA")


def test_foldback_domain_counts_large_free_loops_without_enumerating_members():
    from hop_design.kernel.construction.foldback.domains import solve_foldback_sequence_domain

    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        junction_offset_nt=0,
        loop_length_nt=12,
        annealing_arm_length_bp=3,
    )
    request = _request(_nickase(), target=target)
    program = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]

    domain = solve_foldback_sequence_domain(payload_sequence="GACT", target=target, program=program)

    assert domain.cardinality == 262144
    assert len(domain.independent_domains) == 15
    assert domain.materialize("ACA" + "A" * 12).source_reference_sequence == (
        "GACTACATTTTTTTTTTTTTGT"
    )


def test_foldback_domain_preserves_payload_recognition_exclusion():
    from hop_design.kernel.construction.foldback.domains import solve_foldback_sequence_domain

    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    request = _request(_nickase(motif="GAC", cut_offset=3), target=target)
    program = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]

    outcome = solve_foldback_sequence_domain(
        payload_sequence="GACT", target=target, program=program
    )

    assert outcome.code == "payload-recognition-conflict"


def test_unconstrained_loop_bases_are_enumerated_without_a_sequence_preference() -> None:
    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    request = _request(_nickase(motif="ACANNN"), target=target)
    route = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]

    solutions = tuple(
        iter_foldback_program_solutions(
            payload_sequence="GACA",
            target=target,
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
        junction_offset_nt=1,
        loop_length_nt=4,
        annealing_arm_length_bp=3,
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
        "GACA" + retained_base + "ATTTTTAT" for retained_base in "ACGT"
    )
    assert tuple(solution.retained_sequence for solution in solutions) == tuple(
        "GACA" + retained_base + "ATAAAAAT" + complement + "TGTC"
        for retained_base, complement in zip("ACGT", "TGCA", strict=True)
    )


def test_discovery_preserves_all_exact_loop_realizations_beneath_one_geometry() -> None:
    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    result = discover_foldback_neighborhood(_request(_nickase(motif="ACANTT"), target=target))

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
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
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    result = discover_foldback_neighborhood(
        _request(_nickase(motif="ACANTT"), target=target, max_search_nodes=2)
    )

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.TRUNCATED
    assert (
        result.neighborhood.disposition.termination_reason is SearchTerminationReason.EVALUATION_CAP
    )
    assert tuple(item.loop_sequence for item in result.realizations) == ("AAA", "AAC")
