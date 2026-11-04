"""Numerical proposals cannot replace exact molecular reranking or admission."""

from itertools import product

import pytest

from hop_design.design.construction.navigation.numerical.comparison import PreparedComparison
from hop_design.design.construction.navigation.similarity import comparison_basis
from tests.unit.test_molecular_similarity import molecule


def test_compiled_proposal_metric_tracks_exact_comparison_and_keeps_real_members():
    pytest.importorskip("numba")
    from hop_design.design.construction.navigation.numerical.candidates import MolecularCandidates

    rows = tuple(
        molecule(identity=str(i), loop="".join(word), basal=("AT", "GT")[i % 2], gap=i % 4)
        for i, word in enumerate(product("ACGT", repeat=3))
    )
    with PreparedComparison(rows, comparison_basis(rows)) as comparison:
        candidates = MolecularCandidates(comparison, seed=17)
        for i in range(len(rows)):
            for j in range(len(rows)):
                # Python's compensated float sum can differ by roundoff. Only
                # proposals use this kernel; exact reranking is checked below.
                assert candidates.distance(i, j) == pytest.approx(
                    comparison.distance(i, j), rel=0, abs=1e-15
                )
        proposed = candidates.propose(32)
        assert proposed.shape == (64, 32)
        assert proposed.min() >= 0 and proposed.max() < 64
        assert all(len(set(row)) == 32 for row in proposed)
        candidates.close()
        with pytest.raises(RuntimeError, match="closed"):
            candidates.propose(32)


def test_neighbor_descent_graph_keeps_exact_edges_and_passes_tie_aware_audit():
    pytest.importorskip("numba")
    from hop_design.design.construction.navigation.similarity_neighbors import build_neighbor_graph
    from hop_design.models.construction.variants.neighbors import NeighborSearchSettings

    rows = tuple(
        molecule(identity=str(i), loop="".join(w)) for i, w in enumerate(product("ACGT", repeat=3))
    )
    basis = comparison_basis(rows)
    policy = NeighborSearchSettings(
        strategy="molecular_neighbor_descent", candidates=32, max_candidates=64, audit_queries=64
    )
    graph = build_neighbor_graph(rows, basis, neighbors=5, seed=17, settings=policy)
    assert graph.receipt.strategy == "molecular_neighbor_descent_exact_rerank"
    assert graph.receipt.minimum_recall >= 0.95
    with PreparedComparison(rows, basis) as comparison:
        for i, (neighbors, distances) in enumerate(
            zip(graph.indices, graph.distances, strict=True)
        ):
            for j, distance in zip(neighbors, distances, strict=True):
                assert distance == comparison.distance(i, int(j))
