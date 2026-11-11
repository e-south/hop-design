"""Loop caps use circular drawing geometry without changing molecular addresses."""

from math import hypot
from types import SimpleNamespace

import pytest

from hop_design.export.construction.molecular.inspection_layout import _state_points


@pytest.mark.parametrize("loop_nt", [3, 4, 6, 12])
def test_loop_bases_and_both_stem_junctions_share_a_circle(loop_nt):
    size = loop_nt + 4
    strand = SimpleNamespace(
        strand_id="hairpin",
        sequence="A" * size,
        lineage=[SimpleNamespace(origin_strand=SimpleNamespace(value="primary"))],
    )
    pairs = [
        SimpleNamespace(
            left_strand_id="hairpin",
            right_strand_id="hairpin",
            left_index=i,
            right_index=size - 1 - i,
        )
        for i in range(2)
    ]
    points = _state_points(SimpleNamespace(molecules=[strand], pairings=pairs))
    assert set(points) == {("hairpin", i) for i in range(size)}
    top, bottom = points["hairpin", 1], points["hairpin", loop_nt + 2]
    assert top[0] == bottom[0]
    center_y = (top[1] + bottom[1]) / 2
    x, y = points["hairpin", 2]
    # Equidistance to the stem junction and first loop base determines the center.
    center_x = (x * x - top[0] * top[0] + (y - center_y) ** 2 - (top[1] - center_y) ** 2) / (
        2 * (x - top[0])
    )
    radii = [
        hypot(points["hairpin", i][0] - center_x, points["hairpin", i][1] - center_y)
        for i in range(1, loop_nt + 3)
    ]
    assert max(radii) - min(radii) < 1e-7
    assert all(points["hairpin", i][0] > top[0] for i in range(2, loop_nt + 2))
    assert all(
        hypot(a[0] - b[0], a[1] - b[1]) >= 14
        for a, b in zip(
            [points["hairpin", i] for i in range(1, loop_nt + 2)],
            [points["hairpin", i] for i in range(2, loop_nt + 3)],
            strict=True,
        )
    )
