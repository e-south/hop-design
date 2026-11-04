"""Compact joint source/adapter membership preserves the actual pairing permissions."""

from dataclasses import replace

import pytest

from hop_design.design.construction.basal.traversal import iter_basal_work_units
from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain
from hop_design.kernel.construction.basal.programs import BasalPlacementFailure
from hop_design.kernel.construction.basal.sequence_index import BasalSequenceIndex
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction import BasalPairAllowance, ConstructionEndpoint
from tests.contract.test_basal_construction_discovery import _pairing_constraints, _request


def _domain(allowances, budget, endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX):
    request = _request(endpoint, pairing_constraints=_pairing_constraints(allowances))
    (unit,) = iter_basal_work_units(request, retained_overhead_nt=len(allowances))
    return solve_basal_sequence_domain(
        payload_sequence=unit.payload_sequence,
        target=unit.target.model_copy(update={"max_noncanonical_pairs": budget}),
        endpoint=request.endpoint,
        program=unit.program,
    )


def _sources(domain, forbidden=None):
    # A deliberately independent source restriction; not recomputed by the population.
    size = domain.adapter_span.start.offset
    builder = SequenceSetBuilder(length_nt=size, max_nodes=10000, max_operations=100000)
    root = builder.from_iupac("N" * size)
    if forbidden is not None:
        root = builder.difference(root, builder.from_iupac(forbidden + "N" * (size - 1)))
    return builder.freeze(root)


@pytest.mark.parametrize("budget", [None, 0, 1, 2])
@pytest.mark.parametrize(
    "endpoint",
    [ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, ConstructionEndpoint.CLONE_READY_DUPLEX],
)
def test_population_agrees_with_all_small_exact_candidates(budget, endpoint):
    from hop_design.kernel.construction.basal.sequence_population import BasalSequencePopulation

    domain = _domain(
        (
            BasalPairAllowance.MATCH,
            BasalPairAllowance.ANY,
            BasalPairAllowance.WOBBLE,
            BasalPairAllowance.MISMATCH,
        ),
        budget,
        endpoint,
    )
    index = BasalSequenceIndex.create(domain)
    sources = _sources(domain, forbidden="A")
    expected = {
        (candidate.source_precursor_sequence, candidate.adapter_sequence)
        for ordinal in range(index.cardinality)
        if not isinstance(candidate := index.member_at(ordinal), BasalPlacementFailure)
        and sources.contains(candidate.source_precursor_sequence)
    }
    population = BasalSequencePopulation(index, sources, max_operations=100000)
    actual = [population.member_at(rank) for rank in range(population.cardinality)]
    assert len(actual) == len(expected)
    assert {(p.source_precursor_sequence, p.adapter_sequence) for p in actual} == expected
    assert [(p.source_precursor_sequence, p.adapter_sequence) for p in actual] == sorted(expected)
    for member in actual:
        assert index.member_at(index.rank_of(member)) == member


def test_large_joint_population_recovers_last_member_without_expansion(monkeypatch):
    from hop_design.kernel.construction.basal.sequence_population import BasalSequencePopulation

    domain = _domain((BasalPairAllowance.MATCH,) + (BasalPairAllowance.ANY,) * 19, 1)
    index = BasalSequenceIndex.create(domain)
    population = BasalSequencePopulation(index, _sources(domain), max_operations=100000)
    # 18 free source positions; only the 19 non-proximal pairs may be noncanonical.
    assert population.cardinality == 4**18 * (1 + 19 * 3)
    original = type(domain).materialize
    calls = []

    def record(self, source, adapter):
        calls.append((source, adapter))
        assert len(calls) == 1
        return original(self, source, adapter)

    monkeypatch.setattr(type(domain), "materialize", record)
    last = population.member_at(population.cardinality - 1)
    assert last.source_precursor_sequence == "T" * 18 + "AACCCC"
    assert last.adapter_sequence == "TTT" + "A" * 17
    assert len(calls) == 1


def test_population_exhausted_computing_limit_is_not_empty_support():
    from hop_design.kernel.construction.basal.sequence_population import BasalSequencePopulation

    domain = _domain((BasalPairAllowance.MATCH,) + (BasalPairAllowance.ANY,) * 11, 2)
    with pytest.raises(SequenceSetLimitError):
        BasalSequencePopulation(
            BasalSequenceIndex.create(domain), _sources(domain), max_operations=1
        )


def test_raw_inverse_rejects_a_foreign_sequence():
    domain = _domain((BasalPairAllowance.MATCH,) * 4, 0)
    index = BasalSequenceIndex.create(domain)
    valid = index.member_at(0)
    with pytest.raises(ValueError):
        index.rank_of(
            replace(valid, source_precursor_sequence="T" * len(valid.source_precursor_sequence))
        )
