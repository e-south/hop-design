"""Prepared ranking agrees with the explanatory oracle, including exact ties."""

from types import SimpleNamespace

import pytest

from hop_design.design.construction.navigation.neighbor_work import NeighborWork
from hop_design.design.construction.navigation.neighbors import neighboring_preparations
from hop_design.design.construction.navigation.similarity import comparison_basis, dissimilarity
from tests.unit.test_molecular_similarity import molecule


def test_fast_ranking_preserves_exact_order_and_does_not_claim_controls():
    rows = tuple(
        molecule(identity=f"p{i}", loop=loop, gap=gap)
        for i, loop, gap in (
            (0, "AAAA", 0),
            (1, "AAAC", 0),
            (2, "AAAC", 0),
            (3, "AACA", 1),
            (4, "ACAA", 2),
        )
    )
    basis = comparison_basis(rows)
    paths = [
        {
            "materialized_realization_id": row.identity,
            "matches": row.identity != "p3",
            "values": {"loop_word": "".join(row.sequences["loop"])},
        }
        for row in reversed(rows)
    ]
    choices = SimpleNamespace(
        landscape=lambda: SimpleNamespace(preparations=rows, basis=basis, digest="landscape"),
        query=lambda _: {"paths": paths},
    )
    result = neighboring_preparations(choices, "p0", limit=3, verify_controls=False)
    expected = sorted(
        (dissimilarity(rows[0], row, basis).total, row.identity)
        for row in rows[1:]
        if row.identity != "p3"
    )
    assert [n["materialized_realization_id"] for n in result["neighbors"]] == [
        key for _, key in expected
    ]
    assert all(n["preservation"] == "not_established" for n in result["neighbors"])
    assert result["preservation_requested"] is False
    for row in result["neighbors"]:
        target = next(r for r in rows if r.identity == row["materialized_realization_id"])
        assert row["dissimilarity"] == dissimilarity(rows[0], target, basis).model_dump(mode="json")


def test_cancelled_neighbor_request_does_not_read_its_source():
    work = NeighborWork()
    work.cancelled.set()
    with pytest.raises(ValueError, match="cancelled"):
        neighboring_preparations(SimpleNamespace(), "reference", work=work)
