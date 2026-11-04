"""Auxiliary groups preserve coupled suffixes without expanding free handle words."""

from itertools import product

import pytest

from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.kernel.construction.source_context import (
    SourceContextCompletionGroups,
    protected_context_suffix_nt,
)
from hop_design.models.construction.sequence_sets import SequenceSet


def words_set(words):
    builder = SequenceSetBuilder(length_nt=len(words[0]), max_nodes=1000, max_operations=10000)
    root = 0
    for word in words:
        root = builder.union(root, builder.from_iupac(word))
    return builder.freeze(root)


def groups(sequences, retained):
    return SourceContextCompletionGroups.create(
        sequences,
        protected_suffix_nt=retained,
        max_decisions=1000,
        max_operations=10000,
    )


def test_correlated_completions_stay_with_their_supported_suffix():
    # These are joint constraints, not independent per-position marginals.
    sequences = words_set(("AAAA", "CAAA", "TACC", "GGCC"))
    result = groups(sequences, 2)
    assert result.group_count == 2
    assert [result.suffix_at(i) for i in range(2)] == ["AA", "CC"]
    assert {result.completions(0).member_at(i) for i in range(2)} == {"AAAA", "CAAA"}
    assert {result.completions(1).member_at(i) for i in range(2)} == {"TACC", "GGCC"}
    assert not result.completions(0).contains("GGAA")
    for word in ("AAAA", "CAAA", "TACC", "GGCC"):
        assert result.completions(result.group_of(word)).contains(word)
    with pytest.raises(ValueError):
        result.group_of("GGAA")


@pytest.mark.parametrize("retained", [0, 1, 2, 3, 4])
def test_projection_and_recovery_match_exhaustive_small_domain(retained):
    all_words = ["".join(b) for b in product("ACGT", repeat=4)]
    admitted = [w for w in all_words if (w[0] == w[-1]) or (w[1] == "G" and w[2] == "C")]
    result = groups(words_set(admitted), retained)
    expected = sorted({w[-retained:] if retained else "" for w in admitted})
    assert result.group_count == len(expected)
    recovered = []
    for group, suffix in enumerate(expected):
        assert result.suffix_at(group) == suffix
        completion = result.completions(group)
        observed = [completion.member_at(i) for i in range(completion.cardinality)]
        assert observed == [w for w in admitted if (w[-retained:] if retained else "") == suffix]
        recovered.extend(observed)
    assert sorted(recovered) == admitted


def test_empty_domain_has_no_completion_group():
    b = SequenceSetBuilder(length_nt=4, max_nodes=100, max_operations=100)
    for suffix in (0, 2, 4):
        result = groups(b.freeze(0), suffix)
        assert result.group_count == 0
        with pytest.raises(ValueError):
            result.suffix_at(0)


def test_trillion_word_domain_is_grouped_without_recovering_any_word(monkeypatch):
    b = SequenceSetBuilder(length_nt=24, max_nodes=100, max_operations=100)
    sequences = b.freeze(b.from_iupac("N" * 24))

    def no_words(*args):
        pytest.fail("Projection enumerated a handle word")

    monkeypatch.setattr(SequenceSet, "member_at", no_words)
    result = groups(sequences, 4)
    assert result.group_count == 256
    # Empty protected suffix means one existential completion problem.
    assert groups(sequences, 0).group_count == 1
    assert result.sequences.cardinality == 4**24


def test_late_group_and_completion_are_directly_addressable():
    b = SequenceSetBuilder(length_nt=24, max_nodes=100, max_operations=100)
    result = groups(b.freeze(b.from_iupac("N" * 24)), 4)
    assert result.suffix_at(255) == "TTTT"
    last = result.completions(255)
    assert last.cardinality == 4**20
    assert last.member_at(last.cardinality - 1) == "T" * 24
    assert result.group_of("G" * 20 + "TTTT") == 255


@pytest.mark.parametrize("value", [-1, True, 25, 1.5])
def test_invalid_protected_suffix_is_rejected(value):
    with pytest.raises(ValueError):
        groups(words_set(("A" * 24,)), value)


def test_projection_budget_stop_is_not_empty_support():
    seq = words_set(("AAAA", "CAAA", "TACC", "GGCC"))
    with pytest.raises(SequenceSetLimitError):
        SourceContextCompletionGroups.create(
            seq, protected_suffix_nt=2, max_decisions=1, max_operations=1
        )


@pytest.mark.parametrize(
    "prefix,nick,anneal,gap,end,expected",
    [
        (17, 0, 17, 6, 4, 0),
        (12, 4, 12, 0, 4, 4),
        (12, 0, 12, 12, 4, 4),
        (12, 4, 20, 12, 4, 12),
        (12, 0, 12, 0, 4, 0),
    ],
)
def test_protection_counts_association_and_released_end_reach(
    prefix, nick, anneal, gap, end, expected
):
    assert (
        protected_context_suffix_nt(
            local_prefix_nt=prefix,
            nick_offset_nt=nick,
            adapter_annealing_nt=anneal,
            left_paired_gap_bp=gap,
            left_end_nt=end,
        )
        == expected
    )


def test_protection_rejects_an_unembedded_nick():
    with pytest.raises(ValueError):
        protected_context_suffix_nt(
            local_prefix_nt=3,
            nick_offset_nt=4,
            adapter_annealing_nt=12,
            left_paired_gap_bp=0,
            left_end_nt=4,
        )
