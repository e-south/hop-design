"""Approximate retrieval is audited; every retained edge uses the exact distance."""

from itertools import product

import pytest

from hop_design.design.construction.navigation.similarity import comparison_basis, dissimilarity
from hop_design.design.construction.navigation.similarity_neighbors import build_neighbor_graph
from hop_design.models.construction.variants.neighbors import NeighborSearchSettings
from tests.unit.test_molecular_similarity import molecule


def cohort():
    return tuple(
        molecule(identity=str(i), loop="".join(word), gap=i % 4)
        for i, word in enumerate(product("ACGT", repeat=3))
    )


def test_sparse_edges_are_exact_and_tied_neighbors_have_full_recall():
    pytest.importorskip("scipy")
    rows = cohort()
    basis = comparison_basis(rows)
    policy = NeighborSearchSettings(
        strategy="landmark_candidates",
        landmarks=8,
        candidates=16,
        max_candidates=64,
        audit_queries=64,
    )
    result = build_neighbor_graph(rows, basis, neighbors=5, seed=17, settings=policy)
    assert result.indices.shape == result.distances.shape == (64, 16)
    assert result.receipt.minimum_recall >= 0.95
    assert result.receipt.audit_k == 15
    assert result.receipt.audited_queries == 64
    assert result.receipt.distance_evaluations > 0
    assert (
        result.receipt.graph_digest
        == build_neighbor_graph(
            rows, basis, neighbors=5, seed=17, settings=policy
        ).receipt.graph_digest
    )
    for i, (neighbors, distances) in enumerate(zip(result.indices, result.distances, strict=True)):
        assert neighbors[0] == i and distances[0] == 0
        assert len(set(neighbors)) == len(neighbors)
        for j, distance in zip(neighbors, distances, strict=True):
            assert distance == dissimilarity(rows[i], rows[int(j)], basis).total


def test_failed_recall_never_silently_publishes_a_graph(monkeypatch):
    pytest.importorskip("scipy")
    import hop_design.design.construction.navigation.similarity_neighbors as owner

    monkeypatch.setattr(owner, "audit_neighbors", lambda *a, **k: ((0, 0.25),))
    rows = cohort()
    with pytest.raises(ValueError, match="recall") as failure:
        build_neighbor_graph(
            rows,
            comparison_basis(rows),
            neighbors=5,
            seed=17,
            settings=NeighborSearchSettings(
                strategy="landmark_candidates", candidates=16, max_candidates=16
            ),
        )
    report = failure.value.report
    assert report["minimum_recall"] == 0.25
    assert report["required_recall"] == 0.95
    assert report["candidates_examined_per_query"] == 16
    assert report["audit"][0]["comparison_key"] == rows[0].comparison_key


def test_graph_receipt_rejects_a_strategy_different_from_its_settings():
    from hop_design.models.construction.variants.neighbors import NeighborGraphReceipt

    with pytest.raises(ValueError, match="strategy"):
        NeighborGraphReceipt(
            strategy="molecular_neighbor_descent_exact_rerank",
            settings=NeighborSearchSettings(strategy="landmark_candidates"),
            seed=17,
            signatures=20,
            retained_neighbors=16,
            candidates_examined_per_query=20,
            distance_evaluations=100,
            audit_k=15,
            audited_queries=1,
            structural_classes=1,
            minimum_recall=1.0,
            audit=(
                {
                    "comparison_key": "sha256:" + "a" * 64,
                    "structural_class": "sha256:" + "b" * 64,
                    "recall": 1.0,
                },
            ),
            graph_digest="sha256:" + "c" * 64,
        )


def test_sparse_settings_bound_work_and_legacy_landscape_bytes_stay_unchanged():
    with pytest.raises(ValueError):
        NeighborSearchSettings(candidates=128, max_candidates=64)
    from hop_design.design.construction.navigation.similarity_layout import (
        build_molecular_landscape,
    )
    from hop_design.serialization import canonical_json_bytes

    landscape = build_molecular_landscape((molecule(),), snapshot_digest="sha256:" + "a" * 64)
    assert b'"neighbor_graph"' not in canonical_json_bytes(landscape)
    assert landscape.schema_id == "hop.molecular-landscape/v1"


def test_large_landscape_uses_audited_precomputed_graph_and_freezes_it(monkeypatch):
    pytest.importorskip("umap")
    import hop_design.design.construction.navigation.similarity_layout as owner
    from hop_design.models.construction.variants.landscape import (
        MolecularLandscape,
        SimilarityLayoutSettings,
    )
    from hop_design.serialization import canonical_json_bytes

    monkeypatch.setattr(owner, "MAX_EXACT_SIGNATURES", 4)
    rows = cohort()[:20]
    result = owner.build_molecular_landscape(
        rows,
        snapshot_digest="sha256:" + "a" * 64,
        settings=SimilarityLayoutSettings(epochs=10),
    )
    assert result.schema_id == "hop.molecular-landscape/v2"
    assert result.neighbor_graph.signatures == 20
    assert result.neighbor_graph.minimum_recall == 1.0
    assert len(result.coordinates) == 20
    assert MolecularLandscape.model_validate_json(canonical_json_bytes(result)) == result
    assert result == owner.build_molecular_landscape(
        rows[::-1],
        snapshot_digest=result.snapshot_digest,
        settings=result.settings,
        neighbor_settings=NeighborSearchSettings(),
    )
