"""Short and asymmetric handles preserve exact step lengths at the drawing seam."""

import math
from types import SimpleNamespace

import pytest

from hop_design.export.construction.molecular.inspection_layout import _fan_handles


@pytest.mark.parametrize("left,right", [(0, 0), (1, 2), (5, 5), (3, 12), (15, 1)])
def test_tail_lengths_do_not_change_pairing_or_base_spacing(left, right):
    # Geometry-only state: no new molecular construction or identity is asserted.
    state = SimpleNamespace(
        phase=SimpleNamespace(value="adapter_ligated"),
        molecules=(
            SimpleNamespace(strand_id="upper", sequence="A" * (left + 3)),
            SimpleNamespace(strand_id="lower", sequence="T" * (right + 3)),
        ),
        pairings=tuple(
            SimpleNamespace(
                left_strand_id="upper",
                left_index=left + i,
                right_strand_id="lower",
                right_index=right + i,
            )
            for i in range(3)
        ),
    )
    points = {
        **{("upper", i): (300 + (i - left) * 16, 160) for i in range(left + 3)},
        **{("lower", i): (300 + (i - right) * 16, 204) for i in range(right + 3)},
    }
    result = _fan_handles(state, points)
    assert set(result) == set(points)
    for strand, tail in (("upper", left), ("lower", right)):
        anchor = result[strand, tail]
        for i in range(tail):
            a, b = result[strand, i], result[strand, i + 1]
            assert math.dist(a, b) == pytest.approx(16)
            if tail - i <= 5:
                assert abs(a[0] - b[0]) == pytest.approx(abs(a[1] - b[1]))
            else:
                assert a[1] == pytest.approx(b[1])
        assert result[strand, tail + 1][0] - anchor[0] == 16
    for pair in state.pairings:
        a, b = result["upper", pair.left_index], result["lower", pair.right_index]
        assert a[0] == b[0]
        assert b[1] - a[1] == 44
