"""A source-placement preference is a permutation, not a domain exclusion."""

from itertools import product

import pytest

from hop_design.kernel.construction.context_order import SourceContextOrder
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from tests.unit.test_source_context_population import population


def test_length_interleaving_and_priority_are_invertible_for_every_context():
    from hop_design.design.construction.surveys.context_priority import (
        ContextPriority,
        SourceContextHint,
    )
    from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
    from tests.unit.test_source_context_population import inputs

    policy, enzyme, action = inputs(
        specification={"min_length_nt": 3, "max_length_nt": 4, "base_spec": "N"}
    )
    ordering = ContextPriority(
        policy,
        SourceContextHint("TCAAGTCACTG", 7, enzyme, action),
        DEFAULT_SEQUENCE_LIMITS,
    )
    ranks = [ordering.rank_at(i) for i in range(320)]
    assert ranks[:4] == [0, 237, 1, 64]
    assert set(ranks) == set(range(320))
    assert [ordering.position(rank) for rank in ranks] == list(range(320))


def test_unavailable_priority_keeps_ordinary_context_coverage():
    from hop_design.design.construction.surveys.context_priority import (
        ContextPriority,
        SourceContextHint,
    )
    from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
    from tests.unit.test_source_context_population import inputs

    policy, enzyme, action = inputs()
    limits = DEFAULT_SEQUENCE_LIMITS.model_copy(update={"max_decisions": 1})
    ordering = ContextPriority(policy, SourceContextHint("TCAAGTCACTG", 7, enzyme, action), limits)
    assert [ordering.rank_at(i) for i in range(256)] == list(range(256))
    assert ordering.position(173) == 173


def test_sequence_rank_is_inverse_even_with_skipped_positions_and_shared_decisions():
    builder = SequenceSetBuilder(length_nt=3, max_nodes=100, max_operations=1000)
    root = builder.union(builder.from_iupac("NAR"), builder.from_iupac("CNY"))
    sequences = builder.freeze(root)
    expected = [
        "".join(bases)
        for bases in product("ACGT", repeat=3)
        if (bases[1] == "A" and bases[2] in "AG") or (bases[0] == "C" and bases[2] in "CT")
    ]
    assert [sequences.rank_of(word) for word in expected] == list(range(len(expected)))
    assert [sequences.member_at(i) for i in range(len(expected))] == expected
    with pytest.raises(ValueError, match="member"):
        sequences.rank_of("TTT")


def test_priority_preserves_every_authored_assignment_and_its_address():
    preferred = population(specification="NNNN")
    order = SourceContextOrder.create(preferred, max_decisions=100, max_operations=1000)
    words = ["".join(bases) for bases in product("ACGT", repeat=4)]
    expected = ["GGTC"] + [word for word in words if word != "GGTC"]
    assert [order.member_at(i)[0] for i in range(256)] == expected
    for position, word in enumerate(expected):
        assert order.position(word) == position
        assert order.member_at(position)[1] == words.index(word)
    assert order.member_at(0)[1] == 173
    assert order.member_at(1)[1] == 0
    with pytest.raises(ValueError):
        order.member_at(256)


def test_empty_preference_keeps_the_original_domain():
    preferred = population(local="GCAAGTCACTG", specification="GRTC")
    order = SourceContextOrder.create(preferred, max_decisions=100, max_operations=1000)
    assert [order.member_at(i) for i in range(2)] == [("GATC", 0), ("GGTC", 1)]
    assert order.position("GGTC") == 1


def test_huge_context_domain_seeks_and_inverts_without_enumeration():
    preferred = population(specification="N" * 24, local="ACTG", boundary=0, length=24)
    order = SourceContextOrder.create(preferred, max_decisions=100, max_operations=1000)
    assert preferred.sequences.cardinality == 4**14
    assert order.member_at(0)[0] == "A" * 13 + "GGTCTCAAGTC"
    assert order.member_at(4**14 - 1)[0] == "T" * 13 + "GGTCTCTAGTC"
    assert order.member_at(4**14)[0] == "A" * 24
    assert order.member_at(4**24 - 1) == ("T" * 24, 4**24 - 1)
    for position in (0, 4**14 - 1, 4**14, 4**20, 4**24 - 1):
        word, _ = order.member_at(position)
        assert order.position(word) == position
