"""Source context recovery follows existing semantics without prefix traversal."""

import pytest

from hop_design.design.construction.surveys.contexts import source_context_at
from hop_design.models.construction.complete.composition_domain import (
    source_context_count,
    source_contexts,
)
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
)
from hop_design.models.molecular_state import EndChemistry


@pytest.mark.parametrize(
    "specification",
    ["RNY", {"min_length_nt": 2, "max_length_nt": 4, "base_spec": "R"}],
)
def test_direct_context_recovery_matches_the_complete_declared_order(specification):
    policy = ConstrainedSourceSsdnaPolicy(
        mode="constrain",
        upstream_sequence_spec=specification,
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
    )
    assert [source_context_at(policy, i) for i in range(source_context_count(policy))] == list(
        source_contexts(policy)
    )
    for invalid in (-1, source_context_count(policy), True):
        with pytest.raises(ValueError, match="rank"):
            source_context_at(policy, invalid)


def test_direct_context_recovery_can_reach_the_last_of_four_to_the_hundred():
    policy = ConstrainedSourceSsdnaPolicy(
        mode="constrain",
        upstream_sequence_spec="N" * 100,
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
    )
    assert source_context_at(policy, 4**100 - 1) == "T" * 100


def test_context_schedule_interleaves_lengths_without_changing_canonical_addresses():
    from hop_design.design.construction.surveys.contexts import (
        source_context_position,
        source_context_rank_at,
    )

    policy = ConstrainedSourceSsdnaPolicy(
        mode="constrain",
        upstream_sequence_spec={"min_length_nt": 1, "max_length_nt": 3, "base_spec": "R"},
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
    )
    # Independent finite oracle: words remain lexicographic within each length.
    expected = [
        "A",
        "AA",
        "AAA",
        "G",
        "AG",
        "AAG",
        "GA",
        "AGA",
        "GG",
        "AGG",
        "GAA",
        "GAG",
        "GGA",
        "GGG",
    ]
    ranks = [source_context_rank_at(policy, i) for i in range(14)]
    assert [source_context_at(policy, i) for i in ranks] == expected
    assert sorted(ranks) == list(range(14))
    assert [source_context_position(policy, i) for i in ranks] == list(range(14))
    for invalid in (-1, 14, True):
        with pytest.raises(ValueError, match="rank"):
            source_context_rank_at(policy, invalid)
        with pytest.raises(ValueError, match="rank"):
            source_context_position(policy, invalid)


def test_context_schedule_reaches_each_permitted_length_without_scanning_words():
    from hop_design.design.construction.surveys.contexts import (
        source_context_position,
        source_context_rank_at,
    )

    policy = ConstrainedSourceSsdnaPolicy(
        mode="constrain",
        upstream_sequence_spec={"min_length_nt": 14, "max_length_nt": 24, "base_spec": "N"},
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
    )
    assert [source_context_at(policy, source_context_rank_at(policy, i)) for i in range(11)] == [
        "A" * length for length in range(14, 25)
    ]
    last = source_context_count(policy) - 1
    assert source_context_at(policy, source_context_rank_at(policy, last)) == "T" * 24
    assert source_context_position(policy, last) == last
