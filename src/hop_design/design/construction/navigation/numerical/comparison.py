"""Admission once, bounded regional reuse, and exact numerical pair comparisons."""

from functools import lru_cache
from importlib import import_module
from typing import Any, Self

from hop_design.models.construction.variants.similarity import (
    MolecularComparisonBasis,
    MolecularDescriptor,
)

from ..similarity import regional_difference
from .edit_pattern import EditPattern


class PreparedComparison:
    """Invocation-owned numerical view; neither molecular identity nor admission.

    The public dissimilarity function remains the explanatory reference. This
    view uses its same block order and arithmetic, but hashes members once and
    shares edit distances between repeated regions. No all-pairs table is kept.
    """

    def __init__(
        self,
        rows: tuple[MolecularDescriptor, ...],
        basis: MolecularComparisonBasis,
        *,
        cache_entries: int = 65_536,
    ) -> None:
        if type(cache_entries) is not int or cache_entries < 0:
            raise ValueError("Regional comparison cache size must be a nonnegative integer.")
        members = set(basis.comparison_keys)
        for row in rows:
            if row.scope_key != basis.scope_key:
                raise ValueError("Compared molecules must share the declared comparison scope.")
            if row.comparison_key not in members:
                raise ValueError(
                    "Molecule is outside the declared comparison; create a new edition."
                )
        self._closed = False
        self._size = len(rows)
        self._scales = tuple(basis.shape_scales.values())
        self._weights = basis.weights
        self._policy = basis.effective_policy
        self._policy.validate_end_lengths(rows)
        self._shape = tuple(
            tuple(shape[k] for k in basis.shape_scales)
            for shape in (r.compared_shape for r in rows)
        )
        words: list[tuple[Any, ...]] = []
        codes: dict[tuple[Any, ...], int] = {}

        def encode(tokens: tuple[Any, ...]) -> int:
            if tokens not in codes:
                codes[tokens] = len(words)
                words.append(tokens)
            return codes[tokens]

        self._sequence = tuple(
            tuple(encode(sequence[k]) for k in basis.sequence_keys)
            for sequence in (r.compared_sequences for r in rows)
        )
        self._interface = tuple(
            tuple(encode(tuple((r.interfaces or {})[k])) for k in basis.interface_keys)
            for r in rows
        )
        self._interface_words = tuple(k.endswith("_word") for k in basis.interface_keys)
        self._words = words
        self._lengths = tuple(len(word) for word in words)
        patterns = [EditPattern(word) for word in words]
        self._patterns = patterns

        @lru_cache(maxsize=cache_entries)
        def edits(first: int, second: int, hamming: bool = False) -> int:
            if hamming:
                return sum(a != b for a, b in zip(words[first], words[second], strict=True))
            if len(words[first]) > len(words[second]):
                first, second = second, first
            return patterns[first].distance(words[second])

        self._edits = edits

    def __len__(self) -> int:
        return self._size

    def __enter__(self) -> Self:
        if self._closed:
            raise RuntimeError("Molecular comparison is closed.")
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Release token storage and cached distances, including on interruption."""
        self._edits.cache_clear()
        self._words.clear()
        self._patterns.clear()
        self._shape = self._sequence = self._interface = ()
        self._lengths = ()
        self._closed = True

    def cache_info(self) -> Any:
        return self._edits.cache_info()

    def proposal_data(self) -> dict[str, Any]:
        """Immutable numeric tokens for optional candidate search, never authority."""
        if self._closed:
            raise RuntimeError("Molecular comparison is closed.")
        np = import_module("numpy")
        words = np.zeros((len(self._words), max(self._lengths, default=0)), dtype=np.int32)
        codes: dict[Any, int] = {}
        for i, word in enumerate(self._words):
            for j, token in enumerate(word):
                if token not in codes:
                    codes[token] = len(codes) + 1
                words[i, j] = codes[token]
        arrays = {
            "shape": np.asarray(self._shape, dtype=np.float64),
            "scales": np.asarray(self._scales, dtype=np.float64),
            "sequence": np.asarray(self._sequence, dtype=np.int32),
            "interface": np.asarray(self._interface, dtype=np.int32),
            "interface_words": np.asarray(self._interface_words, dtype=np.bool_),
            "weights": np.asarray(self._weights, dtype=np.float64),
            "lengths": np.asarray(self._lengths, dtype=np.int32),
            "words": words,
        }
        for array in arrays.values():
            array.flags.writeable = False
        arrays["normalized_regions"] = self._policy.regional_metric == "normalized_edit"
        arrays["hamming_ends"] = self._policy.end_word_metric == "hamming"
        return arrays

    def _distance(self, a: int, b: int, *, hamming: bool = False) -> int:
        if a == b:
            return 0
        return self._edits(a, b, hamming) if a < b else self._edits(b, a, hamming)

    def distance(self, left: int, right: int) -> float:
        if self._closed:
            raise RuntimeError("Molecular comparison is closed.")
        if any(type(i) is not int or not 0 <= i < self._size for i in (left, right)):
            raise ValueError("Molecular comparison index is outside the admitted rows.")
        shape = [
            abs(a - b) / scale
            for a, b, scale in zip(self._shape[left], self._shape[right], self._scales, strict=True)
        ]
        sequence = []
        for a, b in zip(self._sequence[left], self._sequence[right], strict=True):
            la, lb = self._lengths[a], self._lengths[b]
            sequence.append(
                regional_difference(
                    self._distance(a, b),
                    la,
                    lb,
                    normalized=self._policy.regional_metric == "normalized_edit",
                )
            )
        interface = []
        for a, b, word in zip(
            self._interface[left], self._interface[right], self._interface_words, strict=True
        ):
            interface.append(
                self._distance(a, b, hamming=self._policy.end_word_metric == "hamming")
                / max(1, self._lengths[a], self._lengths[b])
                if word
                else float(a != b)
            )
        active = [
            (sum(values) / len(values), weight)
            for values, weight in zip((shape, sequence, interface), self._weights, strict=True)
            if values
        ]
        return sum(v * w for v, w in active) / sum(w for _, w in active) if active else 0.0
