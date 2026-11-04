"""Completion traversal scales with protected choices, not disposable handle words."""

import json
from itertools import product

import pytest

from hop_design.design.construction.surveys.completion.domains import ContextCompletionPlan
from hop_design.models.construction.complete.source_preparation.policy import (
    DerivedSourceSsdnaPolicy,
)
from hop_design.models.construction.sequence_sets import SequenceSet
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.support.context_completion import plan, policy


def test_full_handle_length_domain_has_eleven_groups_not_trillions(monkeypatch):
    def fail(*args):
        pytest.fail("Building the completion plan must not recover a context word")

    monkeypatch.setattr(SequenceSet, "member_at", fail)
    result = plan({"min_length_nt": 14, "max_length_nt": 24, "base_spec": "N"}, 0)
    assert result.group_count == 11
    assert result.raw_context_count == 375299879469056


def test_length_and_protected_suffix_are_both_preserved():
    result = plan({"min_length_nt": 14, "max_length_nt": 24, "base_spec": "N"}, 4)
    assert result.group_count == 11 * 256
    first = result.group_at(0)
    last = result.group_at(result.group_count - 1)
    assert first.length_nt == 14 and first.suffix == "AAAA"
    assert last.length_nt == 24 and last.suffix == "TTTT"
    assert first.completion_count == 4**10
    word, rank = last.member_at(last.completion_count - 1)
    assert word == "T" * 24
    assert rank == result.raw_context_count - 1


def test_no_protected_position_is_lost_when_it_covers_the_entire_context():
    result = plan("NACN", 9)
    assert result.group_count == 16
    for i in range(16):
        group = result.group_at(i)
        assert group.completion_count == 1
        word, rank = group.member_at(0)
        assert group.suffix == word and rank == i


def test_fixed_word_preserves_its_exact_only_completion():
    group = plan("CGAT", 2).group_at(0)
    assert group.suffix == "AT"
    assert group.member_at(0) == ("CGAT", 0)


def test_derived_source_is_one_existing_material_policy_not_new_sequence():
    result = ContextCompletionPlan.create(
        DerivedSourceSsdnaPolicy.model_validate_json(
            json.dumps(
                {
                    "mode": "derive",
                    "five_prime_end": "hydroxyl",
                    "three_prime_end": "hydroxyl",
                }
            )
        ),
        protected_suffix_nt=0,
        limits=DEFAULT_SEQUENCE_LIMITS,
    )
    assert result.group_count == result.raw_context_count == 1
    assert result.group_at(0).member_at(0) == (None, 0)


@pytest.mark.parametrize("bad", [-1, True, 1.25])
def test_invalid_protection_is_not_silently_coerced(bad):
    with pytest.raises(ValueError):
        plan("NNNN", bad)


@pytest.mark.parametrize("bad", [-1, 16, True])
def test_invalid_group_address_is_rejected(bad):
    with pytest.raises(ValueError):
        plan("NNNN", 2).group_at(bad)


def test_source_preference_cannot_recombine_suffixes_or_drop_nonpreferred_words():
    # A deliberately supplied exact preference, not a whole-route admission proof.
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    b = SequenceSetBuilder(length_nt=4, max_nodes=100, max_operations=1000)
    preferred = b.freeze(b.from_iupac("GANN"))
    result = ContextCompletionPlan.create(
        policy("NNNN"),
        protected_suffix_nt=2,
        limits=DEFAULT_SEQUENCE_LIMITS,
    )
    group = result.group_at(1, preferred=preferred)  # AC
    assert group.member_at(0) == ("GAAC", 129)
    all_words = [group.member_at(i)[0] for i in range(group.completion_count)]
    assert len(all_words) == len(set(all_words)) == 16
    assert all(w.endswith("AC") for w in all_words)
    assert "AAAC" in all_words and "TTAC" in all_words


def test_recognition_preference_orders_protected_groups_without_losing_words():
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    builder = SequenceSetBuilder(length_nt=4, max_nodes=100, max_operations=1000)
    preferred = builder.freeze(builder.from_iupac("GATT"))
    domain = plan("NNNN", 2)
    first = domain.group_at(0, preferred=preferred)
    assert first.suffix == "TT"
    assert first.member_at(0) == ("GATT", 143)
    groups = [domain.group_at(i, preferred=preferred) for i in range(domain.group_count)]
    assert len({group.suffix for group in groups}) == 16
    words = [group.member_at(i)[0] for group in groups for i in range(group.completion_count)]
    assert len(words) == len(set(words)) == 256
    assert set(words) == {"".join(bases) for bases in product("ACGT", repeat=4)}


def test_preference_outside_permission_cannot_introduce_a_group():
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    builder = SequenceSetBuilder(length_nt=4, max_nodes=100, max_operations=1000)
    preferred = builder.freeze(builder.from_iupac("NNNT"))
    domain = plan("NNNA", 2)
    assert [domain.group_at(i, preferred=preferred).suffix for i in range(domain.group_count)] == [
        "AA",
        "CA",
        "GA",
        "TA",
    ]


def test_conditioning_preserves_canonical_addresses_and_empty_lengths():
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    def condition(pattern):
        b = SequenceSetBuilder(length_nt=len(pattern), max_nodes=100, max_operations=1000)
        return b.freeze(0 if len(pattern) == 2 else b.from_iupac("TTN"))

    result = ContextCompletionPlan.create(
        policy({"min_length_nt": 2, "max_length_nt": 3, "base_spec": "N"}),
        protected_suffix_nt=1,
        limits=DEFAULT_SEQUENCE_LIMITS,
        condition=condition,
    )
    assert result.raw_context_count == 16 + 64
    assert result.admitted_context_count == 4
    assert result.group_count == 4
    assert result.group_at(0).member_at(0) == ("TTA", 16 + 60)
    assert result.group_at(3).member_at(0) == ("TTT", 16 + 63)
