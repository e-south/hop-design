"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_foldback_population_discovery.py

Verifies complete compact foldback populations and replay-bound program support.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from itertools import product

import pytest

from hop_design.design.construction.foldback_space import (
    discover_sequence_space,
    verify_sequence_space,
)
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction import FoldbackGeometryDomain
from hop_design.models.construction.foldback_space import (
    FoldbackSequenceRequest,
    FoldbackSequenceResult,
    SequenceSpaceLimits,
)
from hop_design.models.enzymes import RecognitionOrientationSemantics
from hop_design.models.payload import DegeneratePayload
from tests.contract.test_foldback_construction_discovery import _nickase, _request, _terminus_enzyme
from tests.contract.test_foldback_sequence_admission import _case, _exact_members


def _space_request(*enzymes, **limits):
    source = _request(
        *(enzymes or (_nickase(motif="RYAT"),)),
        domain=FoldbackGeometryDomain(
            junction_offsets_nt=(1,),
            loop_lengths_nt=(3,),
            annealing_arm_lengths_bp=(3,),
        ),
    )
    return FoldbackSequenceRequest(
        payload=source.payload,
        route_family=source.route_family,
        geometry_domain=source.geometry_domain,
        enzyme_provisioning=source.enzyme_provisioning,
        max_retained_overhead_nt=9,
        limits=SequenceSpaceLimits(
            **(
                {
                    "max_cases": 100,
                    "max_programs": 100,
                    "max_decisions": 10000,
                    "max_set_operations": 100000,
                    "max_site_checks": 10000,
                    "max_result_decisions": 100000,
                }
                | limits
            )
        ),
    )


def test_compact_result_covers_every_exact_case_and_matches_exhaustive_members():
    result = discover_sequence_space(_space_request())
    assert result.completion == "complete"
    assert result.candidate_count == 8192
    assert result.admitted_count == 72
    assert len(result.cases) == 2
    for case in result.cases:
        assert case.candidate_count == 4096
        assert case.programs[0].placement_count == 64
        expected = _exact_members(_case(strand=case.target.nick_strand))
        assert {case.sequences.member_at(i) for i in range(36)} == expected
        for bases in product("ACGT", repeat=6):
            word = "".join(bases)
            assert case.sequences.contains(word) is (word in expected)
    assert verify_sequence_space(result) == result
    assert FoldbackSequenceResult.model_validate_json(result.model_dump_json()) == result


def test_aliases_preserve_separate_support_without_multiplying_configuration_counts():
    result = discover_sequence_space(
        _space_request(
            _nickase(motif="RYAT", enzyme_id="example:enzyme/a@1"),
            _nickase(motif="RYAT", enzyme_id="example:enzyme/b@1"),
            _terminus_enzyme(
                motif="AAGC",
                orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
            ),
        )
    )
    assert result.admitted_count == 72
    assert result.candidate_count == 8192
    assert all(len(case.programs) == 6 for case in result.cases)
    for case in result.cases:
        assert sorted(item.sequences.cardinality for item in case.programs) == [
            0,
            0,
            32,
            32,
            36,
            36,
        ]


def test_iupac_payload_members_remain_separate_and_keep_exhausted_absence():
    request = _space_request(_nickase(motif="ACA"))
    payload = request.payload.model_copy(update={"payload": DegeneratePayload(sequence="GACW")})
    request = request.model_copy(update={"payload": payload})
    result = discover_sequence_space(request)
    assert len(result.cases) == 4
    assert result.candidate_count == 16384
    assert {case.payload_sequence for case in result.cases} == {"GACA", "GACT"}
    assert all(
        case.sequences.cardinality == 0 for case in result.cases if case.payload_sequence == "GACA"
    )
    assert any(
        case.sequences.cardinality > 0 for case in result.cases if case.payload_sequence == "GACT"
    )


def test_no_permitted_program_still_records_the_raw_case_population():
    result = discover_sequence_space(_space_request(_terminus_enzyme()))
    assert result.candidate_count == 8192
    assert result.admitted_count == 0
    assert all(case.programs == () and case.sequences.cardinality == 0 for case in result.cases)


def test_placement_exclusion_is_distinct_from_reaction_exhaustion():
    result = discover_sequence_space(_space_request(_nickase(motif="A" * 20)))
    assert result.admitted_count == 0
    assert all(case.programs[0].placement_failure is not None for case in result.cases)


@pytest.mark.parametrize(
    "field",
    (
        "max_cases",
        "max_programs",
        "max_decisions",
        "max_set_operations",
        "max_site_checks",
        "max_result_decisions",
    ),
)
def test_execution_exhaustion_cannot_return_a_complete_empty_result(field):
    with pytest.raises(SequenceSetLimitError, match="budget exhausted"):
        discover_sequence_space(_space_request(**{field: 1}))


def test_verifier_rejects_a_structurally_valid_false_molecular_set():
    result = discover_sequence_space(_space_request())
    empty = result.cases[0].sequences.model_copy(
        update={"root": 0, "decisions": (), "cardinality": 0}
    )
    case = result.cases[0].model_copy(update={"sequences": empty})
    forged = result.model_copy(update={"cases": (case, result.cases[1]), "admitted_count": 36})
    with pytest.raises(ValueError, match="deterministic discovery replay"):
        verify_sequence_space(forged)


def test_verifier_rejects_omitted_case_with_reconciled_totals():
    result = discover_sequence_space(_space_request())
    forged = result.model_copy(
        update={"cases": result.cases[:1], "candidate_count": 4096, "admitted_count": 36}
    )
    with pytest.raises(ValueError, match="deterministic discovery replay"):
        verify_sequence_space(forged)


def test_empty_geometry_envelope_is_complete_without_inventing_cases():
    request = _space_request().model_copy(update={"max_retained_overhead_nt": 8})
    result = discover_sequence_space(request)
    assert result.cases == ()
    assert result.admitted_count == result.candidate_count == 0
    assert verify_sequence_space(result) == result


def test_symbolic_case_limit_is_checked_before_payload_expansion():
    from hop_design.models.construction import FinalPayloadReference
    from hop_design.models.coordinates import Boundary

    request = _space_request().model_copy(
        update={
            "payload": FinalPayloadReference(
                payload=DegeneratePayload(sequence="N" * 100),
                basal_boundary=Boundary(offset=0),
                foldback_boundary=Boundary(offset=100),
            )
        }
    )
    with pytest.raises(SequenceSetLimitError, match="before expansion"):
        discover_sequence_space(request)


@pytest.mark.parametrize("field", ("hop_version", "route_implementation_version"))
def test_verification_binds_the_implementation(field):
    result = discover_sequence_space(_space_request())
    with pytest.raises(ValueError, match="deterministic discovery replay"):
        verify_sequence_space(result.model_copy(update={field: "unrecognized"}))


def test_public_teaching_domain_matches_full_molecular_discovery():
    from pathlib import Path

    import yaml

    from hop_design.design.construction.foldback import discover_foldback_neighborhood
    from hop_design.models.construction import LocalNeighborhoodRequest, NeighborhoodSearchPlan

    path = Path(__file__).resolve().parents[2] / "examples/foldback-sequence-space.yaml"
    request = FoldbackSequenceRequest.model_validate_json(
        json.dumps(yaml.safe_load(path.read_text()))
    )
    control = _request(*request.enzyme_provisioning.catalog.enzymes, domain=request.geometry_domain)
    control = LocalNeighborhoodRequest.model_validate(
        control.model_dump()
        | {
            "search": NeighborhoodSearchPlan(
                max_retained_overhead_nt=10, max_search_nodes=10000, max_realizations=10000
            )
        }
    )
    concrete = discover_foldback_neighborhood(control)
    assert concrete.neighborhood.disposition.completion.value == "complete"
    compact = discover_sequence_space(request)
    assert compact.admitted_count == 190
    assert compact.candidate_count == 163840
    for case in compact.cases:
        start = len(case.payload_sequence)
        stop = start + case.sequences.length_nt
        expected = {
            record.retained_sequence[start:stop]
            for record in concrete.realizations
            if record.local_realization.achieved_geometry == case.target
        }
        assert {case.sequences.member_at(i) for i in range(case.sequences.cardinality)} == expected
