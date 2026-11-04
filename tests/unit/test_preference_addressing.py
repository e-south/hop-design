"""Preferred preparations retain exact admitted addresses and molecular distinctions."""

from dataclasses import replace

import pytest

from hop_design.design.construction.surveys import coordinates
from hop_design.design.construction.surveys.contexts import source_context_at
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.design.construction.surveys.preference_addressing import PreferenceOutOfScope
from hop_design.design.construction.surveys.preference_addressing.source import (
    basal_source_slice,
    source_context_rank,
)
from tests.support.context_completion import policy
from tests.unit.test_basal_population_inverse import _population
from tests.unit.test_interface_survey_compact_foldback import _two_method_product


def test_interleaved_inverse_matches_literal_population_order():
    sizes = (0, 3, 1, 2)
    expected = [(1, 0), (2, 0), (3, 0), (1, 1), (3, 1), (1, 2)]
    for rank, (program, member) in enumerate(expected):
        assert coordinates.interleaved_rank(sizes, program, member) == rank
        assert coordinates.interleaved_at(sizes, rank) == (program, member)


@pytest.mark.parametrize("program,member", [(0, 0), (1, 3), (-1, 0), (4, 0), (True, 0)])
def test_interleaved_inverse_rejects_nonmembers(program, member):
    with pytest.raises(ValueError):
        coordinates.interleaved_rank((0, 3, 1, 2), program, member)


def test_foldback_inverse_matches_exact_sequence_and_oriented_bindings():
    population = PartitionPlans().get(_two_method_product()).foldback
    for rank in range(4):
        program, word = population._member(rank)
        solution = program.domain.materialize(word)
        assert rank in population.ranks_of(solution, program_kind=program.support.kind)
        with pytest.raises(ValueError, match="admitted"):
            population.ranks_of(
                replace(solution, enzyme_bindings=()), program_kind=program.support.kind
            )


def test_foldback_inverse_does_not_visit_preceding_sequence_members(monkeypatch):
    population = PartitionPlans().get(_two_method_product()).foldback
    program, word = population._member(population.parts - 1)
    solution = program.domain.materialize(word)

    def fail(*args, **kwargs):
        pytest.fail("Inverse lookup must not unrank or enumerate preceding members")

    monkeypatch.setattr(type(program.support.sequences), "member_at", fail)
    assert population.parts - 1 in population.ranks_of(solution, program_kind=program.support.kind)


def test_source_context_inverse_preserves_length_first_order_and_constraints():
    spec = policy({"min_length_nt": 1, "max_length_nt": 2, "base_spec": "R"})
    expected = ["A", "G", "AA", "AG", "GA", "GG"]
    for rank, context in enumerate(expected):
        assert source_context_rank(spec, context) == rank
        assert source_context_at(spec, rank) == context
    for excluded in ("", "AAA", "AC", "T"):
        with pytest.raises(PreferenceOutOfScope):
            source_context_rank(spec, excluded)


def test_source_slice_uses_payload_coordinates_even_when_payload_occurs_upstream():
    population = _population()
    domain = population.index.domain
    member = population.member_at(0)
    prefix = domain.payload_sequence
    source = prefix + member.source_precursor_sequence + "TT"
    local, context = basal_source_slice(
        domain=domain,
        source=source,
        payload_start=len(prefix) + member.payload_span.start.offset,
        payload_end=len(prefix) + member.payload_span.end.offset,
    )
    assert local == member.source_precursor_sequence
    assert context == prefix
    with pytest.raises(PreferenceOutOfScope):
        basal_source_slice(domain=domain, source=source, payload_start=0, payload_end=1)
