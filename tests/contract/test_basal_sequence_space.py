"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_basal_sequence_space.py

Checks compact basal populations against complete molecular discovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json

import pytest

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.models.construction import BasalPairAllowance, ConstructionEndpoint
from hop_design.models.enzymes import EnzymeClass
from hop_design.models.payload import DegeneratePayload
from hop_design.models.physical import Strand
from tests.contract.test_basal_construction_discovery import (
    _enzyme,
    _pairing_constraints,
    _provisioning,
    _request,
)


def compact_request(local):
    from hop_design.models.construction.basal_space import BasalSequenceRequest

    return BasalSequenceRequest.model_validate_json(
        json.dumps(
            {
                "schema": "hop.basal-sequence-request/v1",
                "payload": local.payload.model_dump(mode="json"),
                "route_family": local.route_family.value,
                "endpoint": local.endpoint.value,
                "geometry_domain": local.geometry_domain.model_dump(mode="json"),
                "enzyme_provisioning": local.enzyme_provisioning.model_dump(mode="json"),
                "max_retained_overhead_nt": local.search.max_retained_overhead_nt,
                "limits": {
                    "max_cases": 100,
                    "max_programs": 10000,
                    "max_decisions": 10000,
                    "max_set_operations": 100000,
                    "max_site_checks": 10000,
                    "max_result_decisions": 100000,
                },
            }
        )
    )


def canonical_request(
    *, strand=Strand.TOP, endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, aliases=False
):
    local = _request(
        endpoint,
        payload="CCCC" if strand is Strand.TOP else "TTCC",
        pairing_constraints=_pairing_constraints((BasalPairAllowance.MATCH,) * 4),
        extra_nickase=aliases,
    )
    return local.model_copy(
        update={"geometry_domain": local.geometry_domain.model_copy(update={"nick_strand": strand})}
    )


@pytest.mark.parametrize("strand", [Strand.TOP, Strand.BOTTOM])
@pytest.mark.parametrize(
    "endpoint", [ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, ConstructionEndpoint.CLONE_READY_DUPLEX]
)
def test_compact_basal_populations_equal_complete_molecular_members(strand, endpoint):
    from hop_design.design.construction.basal_space import (
        discover_sequence_space,
        verify_sequence_space,
    )

    local = canonical_request(strand=strand, endpoint=endpoint)
    concrete = discover_basal_neighborhood(local)
    assert concrete.discovery.disposition.completion.value == "complete"
    expected = {
        record.source_precursor_sequence[
            record.payload_source_map.segments[0].source_span.start.offset
            - 4 : record.payload_source_map.segments[0].source_span.start.offset
        ]
        for record in concrete.realizations
    }
    result = discover_sequence_space(compact_request(local))
    assert result.candidate_count == 256
    assert len(result.cases) == 1
    sequences = result.cases[0].sequences
    assert {sequences.member_at(i) for i in range(sequences.cardinality)} == expected
    assert result.admitted_count == len(expected)
    assert verify_sequence_space(result) == result


def test_alias_programs_do_not_multiply_local_states_or_raw_population():
    from hop_design.design.construction.basal_space import discover_sequence_space

    one = discover_sequence_space(compact_request(canonical_request()))
    aliases = discover_sequence_space(compact_request(canonical_request(aliases=True)))
    assert one.cases[0].case_id == aliases.cases[0].case_id
    assert one.cases[0].sequences == aliases.cases[0].sequences
    assert one.admitted_count == aliases.admitted_count == 16
    assert one.candidate_count == aliases.candidate_count == 256
    assert len(one.cases[0].programs) == 1
    assert len(aliases.cases[0].programs) == 2


def test_source_context_is_admitted_before_projection_to_the_local_window():
    from hop_design.design.construction.basal_space import discover_sequence_space

    enzyme = _enzyme(
        "example:enzyme/upstream-recognition@1",
        enzyme_class=EnzymeClass.NICKASE,
        pattern="AAC",
        reference_cut=8,
        complement_cut=None,
    )
    local = canonical_request().model_copy(update={"enzyme_provisioning": _provisioning(enzyme)})
    concrete = discover_basal_neighborhood(local)
    assert concrete.discovery.disposition.completion.value == "complete"
    expected = {
        record.source_precursor_sequence[
            record.payload_source_map.segments[0].source_span.start.offset
            - 4 : record.payload_source_map.segments[0].source_span.start.offset
        ]
        for record in concrete.realizations
    }
    result = discover_sequence_space(compact_request(local))
    sequences = result.cases[0].sequences
    assert {sequences.member_at(i) for i in range(sequences.cardinality)} == expected
    assert sequences.contains("AAAA")
    assert not sequences.contains("ACAA")
    assert result.cases[0].programs[0].source_window_start == 4


def test_symbolic_payload_cases_and_geometric_exclusions_remain_explicit():
    from hop_design.design.construction.basal_space import discover_sequence_space

    local = canonical_request()
    local = local.model_copy(
        update={
            "payload": local.payload.model_copy(
                update={"payload": DegeneratePayload(sequence="CCCR")}
            )
        }
    )
    request = compact_request(local)
    result = discover_sequence_space(request)
    assert {case.payload_sequence for case in result.cases} == {"CCCA", "CCCG"}
    assert result.candidate_count == 512
    empty = discover_sequence_space(request.model_copy(update={"max_retained_overhead_nt": 3}))
    assert empty.cases == ()
    assert empty.candidate_count == empty.admitted_count == 0


@pytest.mark.parametrize(
    "resource",
    [
        "max_cases",
        "max_programs",
        "max_decisions",
        "max_set_operations",
        "max_site_checks",
        "max_result_decisions",
    ],
)
def test_exhausted_compact_basal_resources_raise_without_complete_result(resource):
    from hop_design.design.construction.basal_space import discover_sequence_space
    from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError

    local = canonical_request(aliases=True)
    local = local.model_copy(
        update={
            "payload": local.payload.model_copy(
                update={"payload": DegeneratePayload(sequence="CCCR")}
            )
        }
    )
    request = compact_request(local)
    request = request.model_copy(update={"limits": request.limits.model_copy(update={resource: 1})})
    with pytest.raises(SequenceSetLimitError):
        discover_sequence_space(request)


def test_compact_basal_request_rejects_unsupported_pairing_instead_of_narrowing_it():
    with pytest.raises(ValueError, match="canonical"):
        compact_request(_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))


def test_exact_end_programs_are_pooled_without_counting_end_witnesses_twice():
    from hop_design.design.construction.basal_space import discover_sequence_space

    local = canonical_request(endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX)
    local = local.model_copy(
        update={
            "geometry_domain": local.geometry_domain.model_copy(
                update={
                    "future_release": local.geometry_domain.future_release.model_copy(
                        update={"cohesive_end_sequence": "NNNN"}
                    )
                }
            )
        }
    )
    concrete = discover_basal_neighborhood(local)
    assert concrete.discovery.disposition.completion.value == "complete"
    result = discover_sequence_space(compact_request(local))
    assert len(result.cases) == 1
    assert len(result.cases[0].programs) == 256
    expected = {
        record.source_precursor_sequence[
            record.payload_source_map.segments[0].source_span.start.offset
            - 4 : record.payload_source_map.segments[0].source_span.start.offset
        ]
        for record in concrete.realizations
    }
    sequences = result.cases[0].sequences
    assert {sequences.member_at(i) for i in range(sequences.cardinality)} == expected
    assert result.candidate_count == 256


def test_operation_limit_is_molecular_absence_and_preserves_raw_candidates():
    from hop_design.design.construction.basal_space import discover_sequence_space

    local = canonical_request(endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX)
    local = local.model_copy(
        update={
            "enzyme_provisioning": local.enzyme_provisioning.model_copy(
                update={"max_operations": 1}
            )
        }
    )
    result = discover_sequence_space(compact_request(local))
    assert result.candidate_count == 256
    assert result.admitted_count == 0
    assert result.completion == "complete"


@pytest.mark.parametrize("change", ["endpoint", "release", "window"])
def test_compact_request_rejects_inconsistent_molecular_scope(change):
    from hop_design.models.construction.basal_space import BasalSequenceRequest

    local = canonical_request(endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX)
    content = json.loads(compact_request(local).model_dump_json())
    if change == "endpoint":
        content["endpoint"] = "ssdna_hairpin"
    elif change == "release":
        content["geometry_domain"]["future_release"] = None
    else:
        content["geometry_domain"]["pairing_constraints"] = content["geometry_domain"][
            "pairing_constraints"
        ][:1]
    with pytest.raises(ValueError):
        BasalSequenceRequest.model_validate_json(json.dumps(content))


@pytest.mark.parametrize("change", ["membership", "source", "case", "program", "version", "total"])
def test_verified_basal_result_rejects_changed_membership_roster_or_provenance(change):
    from hop_design.design.construction.basal_space import (
        discover_sequence_space,
        verify_sequence_space,
    )
    from hop_design.models.construction.basal_space import BasalSequenceResult

    result = discover_sequence_space(compact_request(canonical_request()))
    content = json.loads(result.model_dump_json())
    if change == "membership":
        content["cases"][0]["sequences"] = {
            "length_nt": 4,
            "decisions": [],
            "root": 0,
            "cardinality": 0,
        }
        content["admitted_count"] = 0
    elif change == "source":
        source = content["cases"][0]["programs"][0]["source_sequences"]
        source.update(decisions=[], root=0, cardinality=0)
    elif change == "case":
        content.update(cases=[], candidate_count=0, admitted_count=0)
    elif change == "program":
        content["cases"][0]["programs"] = []
    elif change == "version":
        content["route_implementation_version"] = "unknown"
    else:
        content["candidate_count"] += 1
    with pytest.raises(ValueError):
        verify_sequence_space(BasalSequenceResult.model_validate_json(json.dumps(content)))
