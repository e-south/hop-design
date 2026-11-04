"""Compact conflict subtraction matches finite oracles and preserves preference."""

import pytest

from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction.sequence_sets import SequenceSet
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.models.sequence import iupac_bases
from tests.support.context_completion import plan


@pytest.mark.parametrize("preferred", [None, "TNNN", "NNAN", "AAAA"])
@pytest.mark.parametrize("patterns", [(), ("ANNN",), ("NCRN", "TNNN"), ("NNNN",)])
def test_exact_seek_matches_word_oracle(preferred, patterns):
    builder = SequenceSetBuilder(length_nt=4, max_nodes=1000, max_operations=10000)
    domain = plan("NWNN", 0).group_at(
        0, preferred=None if preferred is None else builder.freeze(builder.from_iupac(preferred))
    )
    words = [domain.member_at(i)[0] for i in range(domain.completion_count)]
    allowed = [
        i
        for i, word in enumerate(words)
        if not any(all(b in iupac_bases(s) for b, s in zip(word, p, strict=True)) for p in patterns)
    ]
    for start in range(len(words) + 1):
        expected = next((i for i in allowed if i >= start), None)
        assert domain.next_unexcluded(start, patterns, limits=DEFAULT_SEQUENCE_LIMITS) == expected


def test_skip_trillions_without_visiting_them(monkeypatch):
    domain = plan("N" * 24, 0).group_at(0)
    calls = []
    original = SequenceSet.member_at

    def counted(self, rank):
        calls.append(rank)
        return original(self, rank)

    monkeypatch.setattr(SequenceSet, "member_at", counted)
    assert domain.next_unexcluded(1, ("V" + "N" * 23,), limits=DEFAULT_SEQUENCE_LIMITS) == 3 * 4**23
    assert len(calls) <= 50


def test_domain_budget_failure_is_not_an_empty_answer():
    domain = plan("N" * 24, 0).group_at(0)
    with pytest.raises(SequenceSetLimitError):
        domain.next_unexcluded(
            1,
            ("AC" + "N" * 22,),
            limits=DEFAULT_SEQUENCE_LIMITS.model_copy(update={"max_decisions": 1}),
        )
