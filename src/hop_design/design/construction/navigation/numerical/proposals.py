"""Compile a numeric candidate metric; final edge distances use the exact oracle."""

from importlib import import_module
from typing import Any


def proposal_metric(data: dict[str, Any]) -> tuple[Any, Any]:
    """No fastmath, persistent JIT cache, molecular objects or runtime admission.

    Sequential compiled float sums can differ from Python's compensated sum by
    roundoff. These values propose neighbors only; reranking and audit never use
    them as authoritative distances.
    """
    np = import_module("numpy")
    njit = import_module("numba").njit
    shape, scales = data["shape"], data["scales"]
    sequence, interface = data["sequence"], data["interface"]
    interface_words, weights = data["interface_words"], data["weights"]
    lengths, words = data["lengths"], data["words"]
    normalized_regions, hamming_ends = data["normalized_regions"], data["hamming_ends"]

    def edit(first: int, second: int) -> int:
        if first == second:
            return 0
        la, lb = lengths[first], lengths[second]
        previous = np.arange(lb + 1, dtype=np.int32)
        following = np.empty(lb + 1, dtype=np.int32)
        for i in range(la):
            following[0] = i + 1
            for j in range(lb):
                following[j + 1] = min(
                    following[j] + 1,
                    previous[j + 1] + 1,
                    previous[j] + (words[first, i] != words[second, j]),
                )
            previous, following = following, previous
        return int(previous[lb])

    compiled_edit = njit(edit)

    def distance(left: int, right: int) -> float:
        total, active_weight = 0.0, 0.0
        if shape.shape[1]:
            value = 0.0
            for column in range(shape.shape[1]):
                value += abs(shape[left, column] - shape[right, column]) / scales[column]
            total += value / shape.shape[1] * weights[0]
            active_weight += weights[0]
        if sequence.shape[1]:
            value = 0.0
            for column in range(sequence.shape[1]):
                a, b = sequence[left, column], sequence[right, column]
                la, lb = lengths[a], lengths[b]
                edits = compiled_edit(a, b)
                value += (
                    edits / max(1, la, lb)
                    if normalized_regions
                    else min(1.0, max(0, edits - abs(la - lb)) / max(1, min(la, lb)))
                )
            total += value / sequence.shape[1] * weights[1]
            active_weight += weights[1]
        if interface.shape[1]:
            value = 0.0
            for column in range(interface.shape[1]):
                a, b = interface[left, column], interface[right, column]
                if interface_words[column]:
                    edits = 0
                    if hamming_ends:
                        for position in range(lengths[a]):
                            edits += words[a, position] != words[b, position]
                    else:
                        edits = compiled_edit(a, b)
                    value += edits / max(1, lengths[a], lengths[b])
                else:
                    value += 1.0 if a != b else 0.0
            total += value / interface.shape[1] * weights[2]
            active_weight += weights[2]
        return float(total / active_weight) if active_weight else 0.0

    compiled_distance = njit(distance)

    def metric(left: Any, right: Any) -> float:
        return float(compiled_distance(int(left[0]), int(right[0])))

    return compiled_distance, njit(metric)
