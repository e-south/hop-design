"""Fit coordinates once; browsing and frozen rendering need no numeric dependencies."""

from importlib import import_module
from importlib.metadata import version
from typing import Any, Literal

from hop_design.design.runtime import producer_identity
from hop_design.models.construction.variants.landscape import (
    MolecularCoordinate,
    MolecularLandscape,
    SimilarityLayoutSettings,
)
from hop_design.models.construction.variants.neighbors import NeighborSearchSettings
from hop_design.models.construction.variants.similarity import (
    MolecularDescriptor,
    MolecularDistancePolicy,
)

from .numerical.comparison import PreparedComparison
from .similarity import comparison_basis

MAX_EXACT_SIGNATURES = 2048


def _numeric_dependencies() -> Any:
    try:
        numpy = import_module("numpy")
    except ImportError as error:
        raise ValueError(
            "Building molecular coordinates requires hop-design[atlas]. "
            "Viewing a saved molecular landscape does not."
        ) from error
    return numpy


def _fit(
    matrix: Any, settings: SimilarityLayoutSettings
) -> tuple[Any, Literal["classical_mds", "umap"], dict[str, str]]:
    np = _numeric_dependencies()
    n = len(matrix)
    if n <= 3:
        centered = np.eye(n) - np.ones((n, n)) / n
        values, vectors = np.linalg.eigh(-0.5 * centered @ (matrix**2) @ centered)
        order = np.argsort(values)[::-1][:2]
        points = vectors[:, order] * np.sqrt(np.maximum(values[order], 0))
        return points, "classical_mds", {"numpy": version("numpy")}
    try:
        umap = import_module("umap")
    except ImportError as error:
        raise ValueError("Building molecular coordinates requires hop-design[atlas].") from error
    # One job and an explicit seed; no browser-time fit or density inference.
    points = umap.UMAP(
        metric="precomputed",
        n_components=2,
        n_neighbors=min(settings.neighbors, n - 1),
        min_dist=settings.minimum_distance,
        n_epochs=settings.epochs,
        random_state=settings.seed,
        n_jobs=1,
    ).fit_transform(matrix)
    return (
        points,
        "umap",
        {package: version(package) for package in ("numpy", "scipy", "scikit-learn", "umap-learn")},
    )


def build_molecular_landscape(
    preparations: tuple[MolecularDescriptor, ...],
    *,
    snapshot_digest: str,
    settings: SimilarityLayoutSettings | None = None,
    weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
    neighbor_settings: NeighborSearchSettings | None = None,
    distance_policy: MolecularDistancePolicy | None = None,
) -> MolecularLandscape:
    """Coordinates describe compared features; exact preparations remain separate members."""
    if len({p.identity for p in preparations}) != len(preparations):
        raise ValueError("Choose distinct preparations for the molecular landscape.")
    ordered = tuple(sorted(preparations, key=lambda p: p.identity))
    basis = comparison_basis(ordered, weights=weights, policy=distance_policy)
    unique = {p.comparison_key: p for p in ordered}
    signatures = sorted(unique)
    policy = settings or SimilarityLayoutSettings()
    graph_receipt = None
    coordinates: tuple[MolecularCoordinate, ...]
    algorithm: Literal["coincident", "classical_mds", "umap"]
    versions: dict[str, str]
    if len(signatures) == 1:
        coordinates = (MolecularCoordinate(comparison_key=signatures[0], x=0.0, y=0.0),)
        algorithm, versions = "coincident", {}
    else:
        np = _numeric_dependencies()
        rows = tuple(unique[key] for key in signatures)
        if len(signatures) > MAX_EXACT_SIGNATURES or (
            neighbor_settings is not None
            and neighbor_settings != NeighborSearchSettings()
            and len(signatures) > 3
        ):
            from .similarity_neighbors import build_neighbor_graph
            from .similarity_sparse_fit import fit_sparse

            graph = build_neighbor_graph(
                rows,
                basis,
                neighbors=policy.neighbors,
                seed=policy.seed,
                settings=neighbor_settings,
            )
            points, versions = fit_sparse(graph, policy)
            graph_receipt, algorithm = graph.receipt, "umap"
        else:
            matrix = np.zeros((len(signatures), len(signatures)), dtype=np.float64)
            with PreparedComparison(rows, basis) as comparison:
                for i in range(len(signatures)):
                    for j in range(i):
                        matrix[i, j] = matrix[j, i] = comparison.distance(i, j)
            points, algorithm, versions = _fit(matrix, policy)
        points = np.asarray(points, dtype=float)
        points -= points.mean(axis=0)
        # Isotropic scaling preserves the fitted geometry; no axis-wise stretching.
        radius = np.max(np.linalg.norm(points, axis=1))
        if radius > 0:
            points /= radius
        coordinates = tuple(
            MolecularCoordinate(comparison_key=key, x=float(x), y=float(y))
            for key, (x, y) in zip(signatures, points, strict=True)
        )
    return MolecularLandscape(
        schema="hop.molecular-landscape/v2" if graph_receipt else "hop.molecular-landscape/v1",
        snapshot_digest=snapshot_digest,
        basis=basis,
        preparations=ordered,
        coordinates=coordinates,
        algorithm=algorithm,
        settings=policy,
        versions=versions,
        projector=producer_identity(),
        neighbor_graph=graph_receipt,
    )
