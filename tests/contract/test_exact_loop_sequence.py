"""Exact loop intent is enforced in final-strand coordinates in both source orientations."""

import pytest

from hop_design.kernel.construction.foldback.domains import solve_foldback_sequence_domain
from hop_design.kernel.construction.foldback.programs import iter_foldback_programs
from hop_design.models.construction import FoldbackTarget
from hop_design.models.physical import Strand
from tests.contract.test_foldback_construction_discovery import _nickase, _request


@pytest.mark.parametrize("strand", (Strand.TOP, Strand.BOTTOM))
def test_exact_loop_intersects_before_source_materialization(strand):
    target = FoldbackTarget(
        nick_strand=strand,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
        loop_sequence="AGT",
    )
    request = _request(_nickase(motif="ACANNN"), target=target)
    program = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]
    domain = solve_foldback_sequence_domain(payload_sequence="GACA", target=target, program=program)
    assert domain.cardinality == 1
    solution = domain.materialize("ACAAGT")
    assert solution.loop_sequence == "AGT"
    assert solution.retained_sequence == "GACAACAAGTTGTTGTC"
    with pytest.raises(ValueError, match="domain"):
        domain.materialize("ACAAAA")


def test_exact_loop_can_exhaust_a_conflicting_recognition_domain():
    # ACAGGG fixes source-side loop GGG; retained loop is its reverse complement CCC.
    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
        loop_sequence="AAA",
    )
    request = _request(_nickase(motif="ACAGGG"), target=target)
    program = iter_foldback_programs(request.enzyme_provisioning, target=target)[0]
    outcome = solve_foldback_sequence_domain(
        payload_sequence="GACA", target=target, program=program
    )
    assert outcome.code == "foldback-pairing-conflict"
