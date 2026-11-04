"""Joint basal admission agrees with exact molecular replay, including noncanonical pairs."""

import pytest

from hop_design.design.construction.basal.realization import _realization
from hop_design.design.construction.basal.traversal import iter_basal_work_units
from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain
from hop_design.kernel.construction.basal.programs import BasalPlacementFailure
from hop_design.kernel.construction.basal.sequence_index import BasalSequenceIndex
from hop_design.kernel.construction.basal.sequence_population import BasalSequencePopulation
from hop_design.models.construction import BasalPairAllowance, ConstructionEndpoint
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.contract.test_basal_construction_discovery import _pairing_constraints, _request


@pytest.mark.parametrize("budget", [0, 1, 2])
@pytest.mark.parametrize(
    "endpoint", [ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, ConstructionEndpoint.CLONE_READY_DUPLEX]
)
def test_compact_joint_admission_agrees_with_every_exact_small_route(budget, endpoint):
    from hop_design.design.construction.basal_space_admission import admit_basal_source_assignments

    request = _request(
        endpoint,
        pairing_constraints=_pairing_constraints(
            (
                BasalPairAllowance.MATCH,
                BasalPairAllowance.ANY,
                BasalPairAllowance.ANY,
                BasalPairAllowance.MATCH,
                BasalPairAllowance.MATCH,
            )
        ),
    )
    request = request.model_copy(
        update={
            "geometry_domain": request.geometry_domain.model_copy(
                update={"max_noncanonical_pairs": budget}
            )
        }
    )
    (unit,) = iter_basal_work_units(request, retained_overhead_nt=5)
    domain = solve_basal_sequence_domain(
        payload_sequence=unit.payload_sequence,
        target=unit.target,
        endpoint=request.endpoint,
        program=unit.program,
    )
    index = BasalSequenceIndex.create(domain)
    expected = set()
    rejected = 0
    for rank in range(index.cardinality):
        solution = index.member_at(rank)
        if isinstance(solution, BasalPlacementFailure):
            continue
        result = _realization(
            request=request,
            payload_sequence=unit.payload_sequence,
            target=unit.target,
            route=unit.program,
            solution=solution,
        )
        if isinstance(result, str):
            rejected += 1
        else:
            expected.add((solution.source_precursor_sequence, solution.adapter_sequence))
    sources = admit_basal_source_assignments(
        domain=domain, policy=request.enzyme_provisioning, limits=DEFAULT_SEQUENCE_LIMITS
    )
    compact = BasalSequencePopulation(index, sources, max_operations=100000)
    actual = [compact.member_at(i) for i in range(compact.cardinality)]
    assert len(actual) == len(expected)
    assert {(v.source_precursor_sequence, v.adapter_sequence) for v in actual} == expected
    assert expected
    if endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        assert rejected  # The extra AAC site is removed, not merely a pairing-count filter.
