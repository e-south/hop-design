"""Fit only an audited sparse graph, without reconstructing all-pairs distances."""

from importlib import import_module
from importlib.metadata import version
from typing import Any

from hop_design.models.construction.variants.landscape import SimilarityLayoutSettings

from .similarity_neighbors import MolecularNeighborGraph


def fit_sparse(
    graph: MolecularNeighborGraph, settings: SimilarityLayoutSettings
) -> tuple[Any, dict[str, str]]:
    np, umap = import_module("numpy"), import_module("umap")
    n = len(graph.indices)
    # UMAP requires a row array even when neighbors are supplied. Random
    # initialization uses no fake molecular features from this placeholder.
    placeholder = np.zeros((n, 1), dtype=np.float32)
    estimator = umap.UMAP(
        n_components=2,
        n_neighbors=min(settings.neighbors, n - 1),
        min_dist=settings.minimum_distance,
        n_epochs=settings.epochs,
        random_state=settings.seed,
        n_jobs=1,
        init="random",
        force_approximation_algorithm=True,
        precomputed_knn=(graph.indices.copy(), graph.distances.copy(), None),
    )
    points = estimator.fit_transform(placeholder)
    # Detect ignored precomputed neighbors instead of silently fitting placeholders.
    if estimator.knn_indices is None or estimator._small_data:
        raise RuntimeError("UMAP did not consume the audited molecular neighbor graph.")
    packages: tuple[str, ...] = ("numpy", "scipy", "scikit-learn", "umap-learn", "numba")
    if graph.receipt.settings.strategy == "molecular_neighbor_descent":
        packages += ("pynndescent",)
    return points, {package: version(package) for package in packages}
