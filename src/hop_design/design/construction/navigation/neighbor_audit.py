"""Stratified exact checks, with distance ties treated as interchangeable neighbors."""

from collections import defaultdict
from collections.abc import Callable
from heapq import nsmallest
from random import Random
from typing import Any

from hop_design.models.construction.variants.similarity import MolecularDescriptor
from hop_design.serialization import canonical_json_bytes, sha256_digest


class NeighborRecallError(ValueError):
    """Keep the failed query evidence without publishing a low-quality graph."""

    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report
        super().__init__(
            f"Molecular neighbor recall {report['minimum_recall']:.3f} is below "
            f"{report['required_recall']:.3f} with "
            f"{report['candidates_examined_per_query']} candidates. "
            "Inspect the audit, change retrieval settings or use an exact smaller comparison."
        )


def structural_class(row: MolecularDescriptor) -> str:
    return sha256_digest(canonical_json_bytes(row.compared_shape))


def audit_indices(rows: tuple[MolecularDescriptor, ...], count: int, seed: int) -> tuple[int, ...]:
    """Round-robin structural classes, retaining rare classes before repeat members."""
    groups: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        groups[structural_class(row)].append(i)
    rng = Random(seed)
    keys = sorted(groups)
    rng.shuffle(keys)
    for values in groups.values():
        rng.shuffle(values)
    indices: list[int] = []
    while len(indices) < min(count, len(rows)):
        for key in keys:
            if groups[key]:
                indices.append(groups[key].pop())
                if len(indices) == min(count, len(rows)):
                    break
    return tuple(indices)


def audit_neighbors(
    indices: Any,
    distances: Any,
    queries: tuple[int, ...],
    exact: dict[int, tuple[frozenset[int], float]],
    *,
    k: int,
) -> tuple[tuple[int, float], ...]:
    """Recall includes every strictly closer neighbor and only necessary boundary ties."""
    result = []
    for i in queries:
        strict, threshold = exact[i]
        selected = {int(j) for j in indices[i, 1 : k + 1]}
        hits = len(strict & selected)
        ties = sum(float(d) == threshold for d in distances[i, 1 : k + 1])
        result.append((i, (hits + min(k - len(strict), ties)) / k))
    return tuple(result)


def exact_audit_neighbors(
    queries: tuple[int, ...], size: int, distance: Callable[[int, int], float], *, k: int
) -> dict[int, tuple[frozenset[int], float]]:
    result = {}
    for i in queries:
        nearest = nsmallest(k, ((distance(i, j), j) for j in range(size) if j != i))
        threshold = nearest[-1][0]
        result[i] = frozenset(j for d, j in nearest if d < threshold), threshold
    return result
