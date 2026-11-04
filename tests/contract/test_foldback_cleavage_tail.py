"""Check cleaved source-tail choices independently of production materialization."""

from itertools import product

import pytest

from hop_design.kernel.construction.foldback import (
    iter_foldback_program_solutions,
    iter_foldback_programs,
)
from hop_design.models.construction.foldback import FoldbackCleavageProgramKind
from hop_design.models.construction.foldback_replay import replay_foldback_route
from hop_design.models.enzymes import RecognitionOrientationSemantics
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.sequence import reverse_complement_iupac
from tests.contract.test_foldback_sequence_admission import _admit, _case


@pytest.fixture(scope="module")
def exhaustive_sources():
    case = tail_case()
    return {
        "AAA" + "".join(loop): exact_sources(case, "".join(loop))
        for loop in product("ACGT", repeat=3)
    }


def tail_case():
    return _case(
        kind=FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK,
        motif="AAA",
        offset=0,
        displacement=0,
        payload="GCGC",
        terminus_motif="TNNNAC",
        orientations=RecognitionOrientationSemantics.DECLARED_ONLY,
    )


def tail_request():
    from hop_design.models.construction import FoldbackGeometryDomain
    from hop_design.models.payload import ExactPayload
    from tests.contract.test_foldback_population_discovery import _space_request

    _, target, policy, _ = tail_case()
    request = _space_request(*policy.catalog.enzymes)
    return request.model_copy(
        update={
            "payload": request.payload.model_copy(
                update={"payload": ExactPayload(sequence="GCGC")}
            ),
            "geometry_domain": FoldbackGeometryDomain(
                nick_strand=target.nick_strand,
                junction_offsets_nt=(0,),
                annealing_arm_lengths_bp=(3,),
                loop_lengths_nt=(3,),
            ),
        }
    )


def exact_sources(case, loop):
    """Enumerate the 64 TNNNAC tails on an independently specified precursor."""
    domain, target, policy, kind = case
    sources = set()
    for bases in product("ACGT", repeat=3):
        tail = "T" + "".join(bases) + "AC"
        source = "GCGCAAA" + reverse_complement_iupac(loop) + "TTT" + tail
        replay = replay_foldback_route(
            payload_sequence="GCGC",
            target=target,
            program_kind=kind,
            source_reference_sequence=source,
            enzyme_bindings=domain.enzyme_bindings,
        )
        assert replay.ligated_strand.sequence == "GCGCAAA" + loop + "TTTGCGC"
        if not assess_reaction_program(
            program=replay.reaction_program, policy=policy
        ).report.has_errors:
            sources.add(source)
    return sources


@pytest.mark.parametrize(("loop", "feasible"), (("AAA", True), ("CGT", False)))
def test_foldback_admission_does_not_fix_the_cleaved_tail_to_first_bases(loop, feasible):
    case = tail_case()
    sources = exact_sources(case, loop)
    assert bool(sources) is feasible
    assert all(not source.endswith("TAAAAC") for source in sources)
    assert _admit(case).contains("AAA" + loop) is feasible


def test_every_retained_word_matches_independent_source_enumeration(exhaustive_sources):
    admitted = _admit(tail_case())
    assert {admitted.member_at(i) for i in range(admitted.cardinality)} == {
        word for word, sources in exhaustive_sources.items() if sources
    }


def test_concrete_enumeration_keeps_every_cleavage_tail_completion(exhaustive_sources):
    domain, target, policy, kind = tail_case()
    program = next(
        p
        for p in iter_foldback_programs(policy, target=target)
        if p.kind is kind
        and p.nick_orientation is domain.enzyme_bindings[0].orientation
        and p.terminus_orientation is domain.enzyme_bindings[1].orientation
    )
    actual = {
        s.source_reference_sequence
        for s in iter_foldback_program_solutions(
            payload_sequence="GCGC", target=target, program=program
        )
    }
    expected = set().union(*exhaustive_sources.values())
    assert expected <= actual
    assert len(actual) == 64 * 64


def test_public_recovery_preserves_all_locally_valid_tail_choices(tmp_path):
    import json

    from hop_design import construction
    from hop_design.serialization import canonical_json_bytes

    path = tmp_path / "request.json"
    path.write_bytes(canonical_json_bytes(tail_request()))
    receipt = construction.discover_foldback_sequence_space(path)
    result = json.loads(receipt.json_bytes)
    case = result["cases"][0]
    program_index = next(
        i
        for i, p in enumerate(case["programs"])
        if p["kind"] == "sequential_terminus_plus_nick" and p["terminus_orientation"] == "forward"
    )
    expected = exact_sources(tail_case(), "AAA")
    actual = set()
    for completion_rank in range(len(expected)):
        member = json.loads(
            receipt.member_json(
                case_id=case["case_id"],
                rank=0,
                program_index=program_index,
                completion_rank=completion_rank,
            )
        )
        assert member["independent_sequence"] == "AAAAAA"
        assert member["source_completion_count"] == len(expected)
        actual.add(member["realization"]["source_reference_sequence"])
    assert actual == expected
    with pytest.raises(ValueError, match="completion"):
        receipt.member_json(
            case_id=case["case_id"],
            rank=0,
            program_index=program_index,
            completion_rank=len(expected),
        )


def test_atlas_population_keeps_tail_choices_and_inverse_addresses(exhaustive_sources):
    from hop_design.design.construction.foldback_space import discover_sequence_space
    from hop_design.design.construction.surveys.foldback_population import FoldbackPopulation

    population = FoldbackPopulation(discover_sequence_space(tail_request()))
    expected = set().union(*exhaustive_sources.values())
    actual = set()
    ranks = []
    for rank in range(population.parts):
        program, assignment = population._member(rank)
        if (
            program.support.kind is FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK
            and program.support.terminus_orientation.value == "forward"
        ):
            solution = program.domain.materialize(assignment)
            actual.add(solution.source_reference_sequence)
            assert population.loop_sequence(rank) == solution.loop_sequence
            ranks.append((rank, solution, program.support.kind))
    assert actual == expected
    for rank, solution, kind in (ranks[0], ranks[len(ranks) // 2], ranks[-1]):
        assert rank in population.ranks_of(solution, program_kind=kind)


def test_source_partition_extent_and_resume_include_tail_variables():
    from hop_design.design.construction.surveys.partitions import local_extent
    from hop_design.models.payload import ExactPayload
    from tests.contract.test_foldback_construction_discovery import _request

    domain, target, policy, kind = tail_case()
    local = _request(*policy.catalog.enzymes, target=target)
    local = local.model_copy(
        update={
            "payload": local.payload.model_copy(update={"payload": ExactPayload(sequence="GCGC")})
        }
    )
    assert local_extent(local).parts == 4096
    program = next(
        p
        for p in iter_foldback_programs(policy, target=target)
        if p.kind is kind and p.terminus_orientation is domain.enzyme_bindings[1].orientation
    )
    args = {"payload_sequence": "GCGC", "target": target, "program": program}
    full = list(iter_foldback_program_solutions(**args))
    assert full == [
        *iter_foldback_program_solutions(**args, stop=137),
        *iter_foldback_program_solutions(**args, start=137),
    ]


def test_mirrored_tail_keeps_sequence_identity_and_exact_inverse():
    from hop_design.models.physical import Strand

    domain, target, _, kind = tail_case()
    mirrored = domain.mirrored()
    for tail in product("ACGT", repeat=3):
        assignment = "AAAAAA" + "".join(tail)
        source = domain.materialize(assignment)
        reverse = mirrored.materialize(assignment)
        assert reverse.source_reference_sequence == reverse_complement_iupac(
            source.source_reference_sequence
        )
        assert reverse.retained_sequence == source.retained_sequence
        assert mirrored.assignment_of(reverse) == assignment
        replay = replay_foldback_route(
            payload_sequence="GCGC",
            target=target.model_copy(update={"nick_strand": Strand.BOTTOM}),
            program_kind=kind,
            source_reference_sequence=reverse.source_reference_sequence,
            enzyme_bindings=reverse.enzyme_bindings,
        )
        assert replay.ligated_strand.sequence == source.retained_sequence


@pytest.mark.parametrize("limit", ("max_decisions", "max_site_checks", "max_result_decisions"))
def test_tail_resource_exhaustion_is_not_molecular_exclusion(limit):
    from hop_design.design.construction.foldback_space import discover_sequence_space
    from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError

    request = tail_request()
    request = request.model_copy(update={"limits": request.limits.model_copy(update={limit: 1})})
    with pytest.raises(SequenceSetLimitError, match="budget exhausted"):
        discover_sequence_space(request)


def test_recovery_rejects_forged_source_completions_and_old_schema(tmp_path):
    import json

    from hop_design import construction
    from hop_design.design.construction.foldback_space import discover_sequence_space
    from hop_design.serialization import canonical_json_bytes

    result = discover_sequence_space(tail_request())
    mapping = json.loads(canonical_json_bytes(result))
    path = tmp_path / "result.json"
    mapping["schema"] = "hop.foldback-sequence-result/v1"
    path.write_text(json.dumps(mapping))
    with pytest.raises(ValueError, match="Unsupported foldback sequence result schema"):
        construction.load_verified_foldback_sequence_space(path)
    mapping["schema"] = "hop.foldback-sequence-result/v2"
    support = next(
        p
        for p in mapping["cases"][0]["programs"]
        if p["source_assignments"]["length_nt"] > p["sequences"]["length_nt"]
    )
    joint = support["source_assignments"]
    joint.update(root=1, decisions=[], cardinality=4 ** joint["length_nt"])
    path.write_text(json.dumps(mapping))
    with pytest.raises(ValueError, match="deterministic discovery replay"):
        construction.load_verified_foldback_sequence_space(path)


@pytest.mark.parametrize("role", ("foldback-nick", "terminus-definition"))
def test_recognition_before_source_excludes_placement_without_aborting_other_programs(role):
    from hop_design.design.construction.foldback_space import discover_sequence_space

    request = tail_request()
    policy = request.enzyme_provisioning
    enzymes = list(policy.catalog.enzymes)
    if role == "terminus-definition":
        enzymes[1] = enzymes[1].model_copy(
            update={"recognition_pattern": "T" + "N" * 12 + "AC", "recognition_length": 15}
        )
    else:
        enzymes[0] = enzymes[0].model_copy(update={"cut_offset_reference_strand": 20})
    request = request.model_copy(
        update={
            "enzyme_provisioning": policy.model_copy(
                update={"catalog": policy.catalog.model_copy(update={"enzymes": tuple(enzymes)})}
            )
        }
    )
    result = discover_sequence_space(request)
    programs = result.cases[0].programs
    assert f"{role}-recognition-before-source" in {p.placement_failure for p in programs}
    assert result.completion == "complete"
    if role == "terminus-definition":
        assert any(p.source_assignments.cardinality > 1_000_000 for p in programs)
