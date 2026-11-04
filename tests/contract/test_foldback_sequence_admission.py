"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_foldback_sequence_admission.py

Checks exact compact foldback admission against exhaustive molecular replay.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from itertools import product

import pytest

from hop_design.kernel.construction.foldback import iter_foldback_programs
from hop_design.kernel.construction.foldback.admission import admit_foldback_sequences
from hop_design.kernel.construction.foldback.domains import (
    FoldbackSequenceDomain,
    solve_foldback_sequence_domain,
)
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction import FoldbackTarget
from hop_design.models.construction.foldback import FoldbackCleavageProgramKind
from hop_design.models.construction.foldback_replay import replay_foldback_route
from hop_design.models.construction.foldback_replay.substrates import foldback_reaction_substrates
from hop_design.models.construction.sequence_sets import SequenceSet
from hop_design.models.enzymes import EnzymeProvisioningPolicy, RecognitionOrientationSemantics
from hop_design.models.physical import Strand
from hop_design.models.reaction_replay import assess_reaction_program
from tests.contract.test_foldback_construction_discovery import _nickase, _request, _terminus_enzyme


def _case(
    *,
    strand=Strand.TOP,
    kind=FoldbackCleavageProgramKind.SINGLE_CLEAVAGE,
    motif="RYAT",
    offset=0,
    displacement=1,
    payload="GACA",
    terminus_motif="AAGC",
    orientations=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
):
    target = FoldbackTarget(
        nick_strand=strand,
        junction_offset_nt=displacement,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    request = _request(
        _nickase(motif=motif, cut_offset=offset, orientation_semantics=orientations),
        _terminus_enzyme(
            motif=terminus_motif,
            orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        ),
        target=target,
    )
    for program in iter_foldback_programs(request.enzyme_provisioning, target=target):
        if program.kind is not kind:
            continue
        domain = solve_foldback_sequence_domain(
            payload_sequence=payload, target=target, program=program
        )
        if isinstance(domain, FoldbackSequenceDomain):
            return domain, target, request.enzyme_provisioning, kind
    pytest.fail("The synthetic fixture must supply a placement-compatible program.")


def _admit(case, **limits):
    domain, target, policy, kind = case
    return admit_foldback_sequences(
        domain=domain,
        target=target,
        program_kind=kind,
        policy=policy,
        **({"max_nodes": 10000, "max_operations": 100000, "max_site_checks": 10000} | limits),
    )


def _exact_members(case):
    domain, target, policy, kind = case
    expected = set()
    for bases in product(*domain.independent_domains):
        word = "".join(bases)
        solution = domain.materialize(word)
        replay = replay_foldback_route(
            payload_sequence=domain.payload_sequence,
            target=target,
            program_kind=kind,
            source_reference_sequence=solution.source_reference_sequence,
            enzyme_bindings=solution.enzyme_bindings,
        )
        assessment = assess_reaction_program(program=replay.reaction_program, policy=policy)
        if not assessment.report.has_errors:
            expected.add(word)
    return expected


@pytest.mark.parametrize("strand", (Strand.TOP, Strand.BOTTOM))
@pytest.mark.parametrize("kind", tuple(FoldbackCleavageProgramKind))
@pytest.mark.parametrize(
    ("options", "placement_count", "single_count", "sequential_count"),
    (
        ({}, 64, 36, 32),
        ({"offset": -1, "displacement": 0}, 64, 36, 32),
        ({"motif": "RYNNRT", "displacement": 0}, 128, 64, 62),
        ({"motif": "ACANTT", "displacement": 0, "payload": "ACATTT"}, 4, 0, 0),
        ({"motif": "ACANTT", "displacement": 0, "terminus_motif": "ACATTT"}, 4, 4, 0),
    ),
    ids=("variable-sites", "external-cut", "correlated-sites", "payload-site", "discarded-site"),
)
def test_compact_foldback_admission_matches_every_exact_molecular_member(
    strand, kind, options, placement_count, single_count, sequential_count
):
    case = _case(strand=strand, kind=kind, **options)
    domain = case[0]
    sequences = _admit(case)
    expected = _exact_members(case)
    expected_count = (
        single_count if kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE else sequential_count
    )
    assert domain.cardinality == placement_count
    assert len(expected) == expected_count
    assert sequences.cardinality == expected_count
    assert {sequences.member_at(rank) for rank in range(sequences.cardinality)} == expected
    for bases in product(*domain.independent_domains):
        word = "".join(bases)
        assert sequences.contains(word) is (word in expected)
    assert SequenceSet.model_validate_json(sequences.model_dump_json()) == sequences


@pytest.mark.parametrize(
    ("kind", "expected_count"),
    (
        (FoldbackCleavageProgramKind.SINGLE_CLEAVAGE, 44),
        (FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK, 40),
    ),
)
def test_compact_admission_respects_declared_only_recognition(kind, expected_count):
    case = _case(kind=kind, orientations=RecognitionOrientationSemantics.DECLARED_ONLY)
    sequences = _admit(case)
    assert sequences.cardinality == expected_count
    assert {sequences.member_at(rank) for rank in range(expected_count)} == _exact_members(case)


@pytest.mark.parametrize("strand", (Strand.TOP, Strand.BOTTOM))
def test_sequential_replay_retains_discarded_duplex_and_exact_source_coordinates(strand):
    domain, target, policy, kind = _case(
        strand=strand,
        kind=FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK,
        motif="ACANTT",
        displacement=0,
        terminus_motif="ACATTT",
    )
    solution = domain.materialize("ACAAAC")
    replay = replay_foldback_route(
        payload_sequence=domain.payload_sequence,
        target=target,
        program_kind=kind,
        source_reference_sequence=solution.source_reference_sequence,
        enzyme_bindings=solution.enzyme_bindings,
    )
    spans = foldback_reaction_substrates(
        source_nt=len(domain.source_expression),
        program_kind=kind,
        nick_strand=strand,
        terminus=domain.terminus_boundary,
    )
    expected = ((0, 19), (0, 13), (13, 19)) if strand is Strand.TOP else ((0, 19), (6, 19), (0, 6))
    assert (
        tuple((item.source_span.start.offset, item.source_span.end.offset) for item in spans)
        == expected
    )
    state = replay.reaction_program.states[1]
    assert tuple(molecule.molecule_id for molecule in state.molecules) == (
        "source",
        "released-duplex",
    )
    assert state.molecules[1].reference_sequence_5prime == (
        "ACATTT" if strand is Strand.TOP else "AAATGT"
    )
    assessment = assess_reaction_program(program=replay.reaction_program, policy=policy)
    assert any(
        binding.molecule_id == "released-duplex"
        for binding in assessment.stage_assessments[1].undeclared_bindings
    )
    assert _admit((domain, target, policy, kind)).cardinality == 0


@pytest.mark.parametrize("kind", tuple(FoldbackCleavageProgramKind))
def test_compact_admission_enforces_program_operation_limit(kind):
    domain, target, policy, _ = _case(kind=kind)
    policy = EnzymeProvisioningPolicy.model_validate(policy.model_dump() | {"max_operations": 1})
    case = domain, target, policy, kind
    sequences = _admit(case)
    expected = _exact_members(case)
    assert sequences.cardinality == (
        36 if kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE else 0
    )
    assert {sequences.member_at(rank) for rank in range(sequences.cardinality)} == expected


def test_compact_admission_rejects_an_unprovisioned_enzyme():
    domain, target, policy, kind = _case()
    nick_id = domain.enzyme_bindings[0].enzyme_id
    policy = EnzymeProvisioningPolicy.model_validate(
        policy.model_dump()
        | {"allowed_enzyme_ids": (), "forbidden_enzyme_ids": (nick_id,), "role_restrictions": ()}
    )
    case = domain, target, policy, kind
    assert _admit(case).cardinality == 0
    assert _exact_members(case) == set()


@pytest.mark.parametrize("limit", ("max_nodes", "max_operations", "max_site_checks"))
def test_compact_admission_exhaustion_is_not_an_empty_completed_set(limit):
    with pytest.raises(SequenceSetLimitError, match="budget exhausted"):
        _admit(_case(), **{limit: 1})


@pytest.mark.parametrize("limit", (0, True, 1000001))
def test_compact_admission_requires_a_bounded_recognition_scan(limit):
    with pytest.raises(ValueError, match="max_site_checks"):
        _admit(_case(), max_site_checks=limit)
