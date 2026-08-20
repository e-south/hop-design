from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.models.coordinates import BasePairCount, Boundary, NucleotideCount, Span


def test_span_uses_zero_based_half_open_boundaries() -> None:
    span = Span(start=Boundary(offset=2), end=Boundary(offset=7))

    assert span.length == NucleotideCount(value=5)
    assert span.contains_index(2)
    assert span.contains_index(6)
    assert not span.contains_index(7)


@pytest.mark.parametrize(
    "model",
    [
        lambda: Boundary(offset=-1),
        lambda: NucleotideCount(value=-1),
        lambda: BasePairCount(value=-1),
    ],
)
def test_coordinate_values_reject_negative_numbers(model: object) -> None:
    with pytest.raises(ValidationError):
        model()  # type: ignore[operator]


def test_span_rejects_reversed_boundaries() -> None:
    with pytest.raises(ValidationError, match="end boundary"):
        Span(start=Boundary(offset=4), end=Boundary(offset=3))


def test_count_types_are_not_interchangeable() -> None:
    class PairContract(BasePairCount):
        pass

    with pytest.raises(ValidationError):
        PairContract(value=NucleotideCount(value=3))
