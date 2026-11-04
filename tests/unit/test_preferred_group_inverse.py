"""Direct group lookup preserves the exact preferred-first suffix ordering."""

import pytest

from hop_design.design.construction.surveys.completion import group_preference
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.kernel.construction.source_context import SourceContextCompletionGroups
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS


def test_direct_inverse_of_known_suffix_order_without_traversal(monkeypatch):
    builder = SequenceSetBuilder(length_nt=4, max_nodes=100, max_operations=1000)
    all_words = builder.freeze(builder.from_iupac("NNNN"))
    preferred = builder.freeze(builder.from_iupac("NNGT"))
    groups = SourceContextCompletionGroups.create(
        all_words, protected_suffix_nt=2, max_decisions=100, max_operations=1000
    )
    # GT is canonical suffix 11; all other suffixes remain in base order.
    order = [11, *[i for i in range(16) if i != 11]]
    monkeypatch.setattr(
        group_preference,
        "preferred_group_index",
        lambda *a, **k: pytest.fail("Inverse lookup must not enumerate the forward permutation"),
    )
    for canonical in range(16):
        assert group_preference.preferred_group_position(
            groups, canonical, preferred, limits=DEFAULT_SEQUENCE_LIMITS
        ) == order.index(canonical)
