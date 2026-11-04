"""Inverse addresses preserve admitted joint order without enumerating predecessors."""

from dataclasses import replace

import pytest

from hop_design.kernel.construction.basal.conditioned_population import ConditionedBasalPopulation
from hop_design.kernel.construction.basal.programs import BasalPlacementFailure
from hop_design.kernel.construction.basal.sequence_index import BasalSequenceIndex
from hop_design.kernel.construction.basal.sequence_population import BasalSequencePopulation
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.models.construction import BasalPairAllowance, ConstructionEndpoint
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.unit.test_basal_sequence_population import _domain, _sources


def _population(budget=1, endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX):
    domain = _domain((BasalPairAllowance.MATCH,) + (BasalPairAllowance.ANY,) * 3, budget, endpoint)
    index = BasalSequenceIndex.create(domain)
    size = domain.adapter_span.start.offset
    builder = SequenceSetBuilder(length_nt=size, max_nodes=10000, max_operations=100000)
    # Each variable base is allowed individually; their joint relationship is restrictive.
    variable = [position for position, mask in enumerate(index.source_domains()) if len(mask) > 1]
    patterns = []
    for base in "AC":
        pattern = ["N"] * size
        for position in variable[:2]:
            pattern[position] = base
        patterns.append("".join(pattern))
    root = builder.union(
        builder.from_iupac(patterns[0]),
        builder.from_iupac(patterns[1]),
    )
    return BasalSequencePopulation(index, builder.freeze(root), max_operations=100000)


@pytest.mark.parametrize("budget", [None, 0, 1, 2])
@pytest.mark.parametrize(
    "endpoint", [ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, ConstructionEndpoint.CLONE_READY_DUPLEX]
)
def test_inverse_agrees_with_literal_small_population_order(budget, endpoint):
    population = _population(budget, endpoint)
    expected = sorted(
        (
            member
            for raw in range(population.index.cardinality)
            if not isinstance(member := population.index.member_at(raw), BasalPlacementFailure)
            and population.sources.contains(member.source_precursor_sequence)
        ),
        key=lambda member: (member.source_precursor_sequence, member.adapter_sequence),
    )
    assert len(expected) == population.cardinality
    if not expected:
        with pytest.raises(ValueError):
            population.rank_of(_population(None, endpoint).member_at(0))
    for rank, member in enumerate(expected):
        assert population.rank_of(member) == rank
        assert population.member_at(rank) == member


def test_inverse_preserves_extra_adapter_context_order():
    domain = _population().index.domain
    size = len(domain.base_domains)
    extended = replace(
        domain,
        base_domains=(*domain.base_domains, ("A", "T"), ("C", "G")),
        unresolved_indexes=(*domain.unresolved_indexes, size, size + 1),
    )
    population = BasalSequencePopulation(
        BasalSequenceIndex.create(extended), _sources(extended), max_operations=100000
    )
    for rank in range(8):
        member = population.member_at(rank)
        assert population.rank_of(member) == rank
    assert [population.member_at(rank).adapter_sequence[-2:] for rank in range(4)] == [
        "AC",
        "AG",
        "TC",
        "TG",
    ]


def test_inverse_rejects_source_correlation_and_pair_budget_violations():
    population = _population(0)
    unrestricted = BasalSequencePopulation(
        population.index, _sources(population.index.domain), max_operations=100000
    )
    excluded = next(
        member
        for rank in range(unrestricted.cardinality)
        if not population.sources.contains(
            (member := unrestricted.member_at(rank)).source_precursor_sequence
        )
    )
    with pytest.raises(ValueError):
        population.rank_of(excluded)
    relaxed = _population(None)
    noncanonical = next(
        member
        for rank in range(relaxed.cardinality)
        if isinstance(
            population.index.domain.materialize(
                (member := relaxed.member_at(rank)).source_precursor_sequence,
                member.adapter_sequence,
            ),
            BasalPlacementFailure,
        )
    )
    with pytest.raises(ValueError):
        population.rank_of(noncanonical)
    with pytest.raises(ValueError):
        population.rank_of(replace(population.member_at(0), enzyme_bindings=()))


def test_inverse_locates_large_population_member_without_unranking(monkeypatch):
    domain = _domain((BasalPairAllowance.MATCH,) + (BasalPairAllowance.ANY,) * 19, 1)
    population = BasalSequencePopulation(
        BasalSequenceIndex.create(domain), _sources(domain), max_operations=100000
    )
    rank = population.cardinality - 1
    member = population.member_at(rank)
    assert rank > 10**12

    def forbid_unranking(*args):
        pytest.fail("Inverse lookup must not visit sequence members.")

    monkeypatch.setattr(BasalSequencePopulation, "member_at", forbid_unranking)
    monkeypatch.setattr(BasalSequenceIndex, "member_at", forbid_unranking)
    assert population.rank_of(member) == rank


def test_conditioned_inverse_uses_conditioned_order_and_rejects_excluded_members(monkeypatch):
    original = _population()
    chosen = [original.member_at(rank) for rank in (1, 4, original.cardinality - 1)]
    builder = SequenceSetBuilder(
        length_nt=len(original.index.domain.base_domains), max_nodes=10000, max_operations=100000
    )
    root = 0
    for member in chosen:
        root = builder.union(
            root, builder.from_iupac(member.source_precursor_sequence + member.adapter_sequence)
        )
    population = ConditionedBasalPopulation(original, builder.freeze(root), DEFAULT_SEQUENCE_LIMITS)
    assert population.cardinality == len(chosen)
    actual = [population.member_at(rank) for rank in range(population.cardinality)]
    assert set(actual) == set(chosen)
    excluded = original.member_at(0)

    def forbid_unranking(*args):
        pytest.fail("Conditioned inverse lookup must not visit sequence members.")

    monkeypatch.setattr(BasalSequencePopulation, "member_at", forbid_unranking)
    monkeypatch.setattr(ConditionedBasalPopulation, "member_at", forbid_unranking)
    for rank, member in enumerate(actual):
        assert population.rank_of(member) == rank
    with pytest.raises(ValueError):
        population.rank_of(excluded)
    with pytest.raises(ValueError):
        population.rank_of(replace(chosen[0], enzyme_bindings=()))


def test_empty_conditioned_population_rejects_member():
    original = _population()
    builder = SequenceSetBuilder(
        length_nt=len(original.index.domain.base_domains), max_nodes=10000, max_operations=100000
    )
    population = ConditionedBasalPopulation(original, builder.freeze(0), DEFAULT_SEQUENCE_LIMITS)
    with pytest.raises(ValueError):
        population.rank_of(original.member_at(0))
