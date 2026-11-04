"""New defaults agree across entry points; captured legacy policies keep their meaning."""

import copy

import pytest

from hop_design.models.construction.variants.neighbors import (
    NeighborGraphReceipt,
    NeighborSearchSettings,
)
from hop_design.serialization import canonical_json_bytes
from tests.unit.test_molecular_similarity import molecule


def legacy_receipt():
    return {
        "schema": "hop.molecular-neighbor-graph/v1",
        "strategy": "landmark_candidates_exact_rerank",
        "settings": {
            "landmarks": 32,
            "candidates": 128,
            "max_candidates": 2048,
            "audit_queries": 128,
            "required_recall": 0.95,
        },
        "seed": 17,
        "signatures": 20,
        "retained_neighbors": 16,
        "candidates_examined_per_query": 20,
        "distance_evaluations": 100,
        "audit_k": 15,
        "audited_queries": 1,
        "structural_classes": 1,
        "minimum_recall": 1.0,
        "audit": [
            {
                "comparison_key": "sha256:" + "a" * 64,
                "structural_class": "sha256:" + "b" * 64,
                "recall": 1.0,
            }
        ],
        "graph_digest": "sha256:" + "c" * 64,
    }


def test_current_defaults_and_standalone_explicit_policies_roundtrip():
    default = NeighborSearchSettings()
    assert default.strategy == "molecular_neighbor_descent" and default.candidates == 64
    for policy in (default, NeighborSearchSettings(strategy="landmark_candidates")):
        assert NeighborSearchSettings.model_validate_json(canonical_json_bytes(policy)) == policy


def test_legacy_receipt_bytes_and_missing_field_meanings_are_preserved():
    original = legacy_receipt()
    before = copy.deepcopy(original)
    restored = NeighborGraphReceipt.model_validate_json(canonical_json_bytes(original))
    assert restored.settings.strategy == "landmark_candidates"
    assert canonical_json_bytes(restored) == canonical_json_bytes(before)
    original["settings"] = {}
    sparse = NeighborGraphReceipt.model_validate_json(canonical_json_bytes(original))
    assert sparse.settings.strategy == "landmark_candidates" and sparse.settings.candidates == 128
    assert original["settings"] == {}


@pytest.mark.parametrize("count", [1, 3, 4, 5, 6])
def test_explicit_default_settings_do_not_change_layout_branch(monkeypatch, count):
    np = pytest.importorskip("numpy")
    from hop_design.design.construction.navigation import similarity_layout, similarity_neighbors

    monkeypatch.setattr(similarity_layout, "MAX_EXACT_SIGNATURES", 5)
    monkeypatch.setattr(
        similarity_layout,
        "_fit",
        lambda matrix, _: (np.zeros((len(matrix), 2)), "classical_mds", {"test": "exact"}),
    )

    class SparseReached(Exception):
        pass

    def sparse(*args, **kwargs):
        raise SparseReached()

    monkeypatch.setattr(similarity_neighbors, "build_neighbor_graph", sparse)
    rows = tuple(molecule(identity=str(i), gap=i) for i in range(count))
    for settings in (None, NeighborSearchSettings()):
        if count > 5:
            with pytest.raises(SparseReached):
                similarity_layout.build_molecular_landscape(
                    rows, snapshot_digest="sha256:" + "a" * 64, neighbor_settings=settings
                )
        else:
            result = similarity_layout.build_molecular_landscape(
                rows, snapshot_digest="sha256:" + "a" * 64, neighbor_settings=settings
            )
            assert result.neighbor_graph is None
