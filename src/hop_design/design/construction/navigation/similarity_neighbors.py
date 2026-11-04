"""Bounded landmark retrieval, exact molecular reranking and measured neighbor recall."""

from contextlib import ExitStack
from dataclasses import dataclass
from importlib import import_module
from random import Random
from typing import Any

from hop_design.models.construction.variants.neighbors import (
    NeighborAuditQuery,
    NeighborGraphReceipt,
    NeighborSearchSettings,
)
from hop_design.models.construction.variants.similarity import (
    MolecularComparisonBasis,
    MolecularDescriptor,
)
from hop_design.serialization import sha256_digest

from .neighbor_audit import (
    NeighborRecallError,
    audit_indices,
    audit_neighbors,
    exact_audit_neighbors,
    structural_class,
)
from .numerical.comparison import PreparedComparison


@dataclass(frozen=True)
class MolecularNeighborGraph:
    indices: Any
    distances: Any
    receipt: NeighborGraphReceipt


def build_neighbor_graph(
    rows: tuple[MolecularDescriptor, ...],
    basis: MolecularComparisonBasis,
    *,
    neighbors: int,
    seed: int,
    settings: NeighborSearchSettings | None = None,
) -> MolecularNeighborGraph:
    """No triangle-inequality pruning: proposals precede an exact molecular audit.

    Working storage is linear in N at a fixed candidate budget. Neighbor
    descent retains its candidate graph; landmark retrieval uses bounded batches.
    Neither strategy allocates an NxN molecular distance matrix.
    A failed audit widens retrieval or raises, never publishes unmeasured quality.
    """
    policy = settings or NeighborSearchSettings()
    n = len(rows)
    if n < 2 or not 2 <= neighbors <= 200:
        raise ValueError("Neighbor search requires at least two rows and 2-200 neighbors.")
    np = import_module("numpy")
    width = min(n, max(16, neighbors))
    if policy.max_candidates < width:
        raise ValueError("Candidate budget is smaller than the retained neighborhood.")
    queries = audit_indices(rows, policy.audit_queries, seed)
    audit_k = min(15, n - 1)
    calls = 0
    with ExitStack() as resources:
        comparison = resources.enter_context(PreparedComparison(rows, basis))

        def distance(i: int, j: int) -> float:
            nonlocal calls
            calls += 1
            return comparison.distance(i, j)

        candidate_index = None
        if policy.strategy == "landmark_candidates":
            landmarks = sorted(Random(seed).sample(range(n), min(n, policy.landmarks)))
            features = np.empty((n, len(landmarks)), dtype=np.float64)
            for i in range(n):
                features[i] = [distance(i, j) for j in landmarks]
            tree = import_module("scipy.spatial").cKDTree(features)
        else:
            from .numerical.candidates import MolecularCandidates

            candidate_index = MolecularCandidates(comparison, seed=seed)
            resources.callback(candidate_index.close)
        exact = exact_audit_neighbors(queries, n, distance, k=audit_k)
        candidates = min(n, max(width, policy.candidates))
        while True:
            indices = np.empty((n, width), dtype=np.int32)
            distances = np.empty((n, width), dtype=np.float64)
            proposed_graph = (
                None if candidate_index is None else candidate_index.propose(candidates)
            )
            for start in range(0, n, 128):
                stop = min(n, start + 128)
                if proposed_graph is None:
                    _, proposals = tree.query(features[start:stop], k=candidates, workers=1)
                else:
                    proposals = proposed_graph[start:stop]
                for i, proposed in zip(range(start, stop), proposals, strict=True):
                    ordered = sorted(
                        ((distance(i, int(j)), int(j)) for j in set(proposed) if j != i),
                    )[: width - 1]
                    # Always include self, even when equal landmark vectors tie.
                    indices[i] = [i, *(j for _, j in ordered)]
                    distances[i] = [0.0, *(d for d, _ in ordered)]
            audit = audit_neighbors(indices, distances, queries, exact, k=audit_k)
            minimum = min(recall for _, recall in audit)
            if minimum >= policy.required_recall:
                break
            if candidates >= min(n, policy.max_candidates):
                raise NeighborRecallError(
                    {
                        "schema": "hop.molecular-neighbor-failure/v1",
                        "scope_key": basis.scope_key,
                        "settings": policy.model_dump(mode="json"),
                        "seed": seed,
                        "signatures": n,
                        "distance_evaluations": calls,
                        "candidates_examined_per_query": candidates,
                        "minimum_recall": minimum,
                        "required_recall": policy.required_recall,
                        "audit_k": audit_k,
                        "audit": [
                            {"comparison_key": rows[i].comparison_key, "recall": recall}
                            for i, recall in audit
                        ],
                    }
                )
            candidates = min(n, policy.max_candidates, candidates * 2)
    digest = sha256_digest(indices.astype("<i4").tobytes() + distances.astype("<f8").tobytes())
    receipt = NeighborGraphReceipt(
        strategy=(
            "landmark_candidates_exact_rerank"
            if policy.strategy == "landmark_candidates"
            else "molecular_neighbor_descent_exact_rerank"
        ),
        settings=policy,
        seed=seed,
        signatures=n,
        retained_neighbors=width,
        candidates_examined_per_query=candidates,
        distance_evaluations=calls,
        audit_k=audit_k,
        audited_queries=len(queries),
        structural_classes=len({structural_class(row) for row in rows}),
        minimum_recall=minimum,
        audit=tuple(
            NeighborAuditQuery(
                comparison_key=rows[i].comparison_key,
                structural_class=structural_class(rows[i]),
                recall=recall,
            )
            for i, recall in audit
        ),
        graph_digest=digest,
    )
    indices.flags.writeable = distances.flags.writeable = False
    return MolecularNeighborGraph(indices, distances, receipt)
