"""Approximate proposals using molecular features; exact reranking owns every edge."""

from importlib import import_module
from typing import Any

from .comparison import PreparedComparison
from .proposals import proposal_metric


class MolecularCandidates:
    """Invocation-owned neighbor descent, never a compatibility or identity test."""

    def __init__(self, comparison: PreparedComparison, *, seed: int) -> None:
        self._np = import_module("numpy")
        self._size = len(comparison)
        self._seed = seed
        self._distance, self._metric = proposal_metric(comparison.proposal_data())
        self._closed = False

    def distance(self, left: int, right: int) -> float:
        if self._closed:
            raise RuntimeError("Molecular candidate index is closed.")
        return float(self._distance(left, right))

    def propose(self, count: int) -> Any:
        if self._closed:
            raise RuntimeError("Molecular candidate index is closed.")
        if not 1 <= count <= self._size:
            raise ValueError("Candidate count lies outside the comparison cohort.")
        if count == self._size:
            return self._np.broadcast_to(self._np.arange(count), (count, count))
        index = import_module("pynndescent").NNDescent(
            self._np.arange(self._size, dtype=self._np.int32).reshape(-1, 1),
            metric=self._metric,
            n_neighbors=count,
            random_state=self._seed,
            n_jobs=1,
            tree_init=False,
            low_memory=True,
        )
        # Integers address the admitted feature table; they are not Euclidean
        # molecular coordinates. No random-projection tree on row IDs is used.
        proposed = index.neighbor_graph[0].copy()
        if proposed.min() < 0 or proposed.max() >= self._size:
            raise ValueError("Neighbor descent did not return complete candidate rows.")
        return proposed

    def close(self) -> None:
        # Dropping both compiled closures releases their captured feature arrays.
        self._distance = self._metric = None
        self._closed = True
