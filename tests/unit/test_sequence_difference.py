"""Literal examples distinguish unique edit correspondence from repeated-base ambiguity."""

import pytest

from hop_design.design.construction.projections.sequence_difference import compare_sequence_region


@pytest.mark.parametrize(
    "before,after,kind,left,right",
    [
        ("ACGT", "ACCT", "substitution", 2, 2),
        ("ACT", "ACGT", "added", None, 2),
        ("ACGT", "ACT", "removed", 2, None),
    ],
)
def test_unique_minimum_edit_correspondence(before, after, kind, left, right):
    result = compare_sequence_region(
        "loop", before, after, (10, 10 + len(before)), (10, 10 + len(after))
    )
    assert result.correspondence == "unique_minimum_edit"
    changed = [c for c in result.columns if c.kind != "unchanged"]
    assert [(c.kind, c.reference_offset, c.observed_offset) for c in changed] == [
        (kind, left, right)
    ]


def test_repeat_length_change_does_not_invent_an_added_base_position():
    result = compare_sequence_region("loop", "AAA", "AAAA", (10, 13), (10, 14))
    assert result.correspondence == "ambiguous_minimum_edit"
    assert result.length_delta == 1
    assert result.columns == ()


def test_equal_sequence_with_shifted_coordinates_is_not_a_sequence_edit():
    result = compare_sequence_region("closing_return", "ACGT", "ACGT", (10, 14), (11, 15))
    assert result.correspondence == "identical"
    assert result.coordinates_changed is True
    assert all(c.kind == "unchanged" for c in result.columns)


def test_comparison_bound_is_honest_and_spans_cannot_lie():
    result = compare_sequence_region("loop", "A" * 300, "A" * 301, (0, 300), (0, 301))
    assert result.correspondence == "unresolved_budget"
    assert result.length_delta == 1 and result.columns == ()
    with pytest.raises(ValueError, match="spans"):
        compare_sequence_region("loop", "AC", "AC", (0, 1), (0, 2))


def test_cached_correspondence_keeps_coordinate_identity_and_ambiguity():
    compare_sequence_region.cache_clear()
    first = compare_sequence_region("loop", "AAAC", "AACA", (2, 6), (2, 6))
    again = compare_sequence_region("loop", "AAAC", "AACA", (2, 6), (2, 6))
    shifted = compare_sequence_region("loop", "AAAC", "AACA", (3, 7), (2, 6))
    assert again == first
    assert first.correspondence == "ambiguous_minimum_edit"
    assert shifted.coordinates_changed and shifted.reference_span == (3, 7)
    assert compare_sequence_region.cache_info().hits == 1
    assert compare_sequence_region.cache_info().maxsize == 64
