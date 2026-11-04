"""Exact unit-cost edit distances with reusable bit masks over arbitrary tokens."""

from typing import Any


class EditPattern:
    """Myers bit-vector recurrence, using unbounded integers rather than truncation.

    This is only a numeric kernel. It neither aligns molecular positions nor
    establishes ancestry; the public dynamic program remains its test oracle.
    """

    def __init__(self, tokens: tuple[Any, ...]) -> None:
        self.length = len(tokens)
        self._masks: dict[Any, int] = {}
        for index, token in enumerate(tokens):
            self._masks[token] = self._masks.get(token, 0) | (1 << index)
        self._width = (1 << self.length) - 1
        self._high = 1 << (self.length - 1) if self.length else 0

    def distance(self, tokens: tuple[Any, ...]) -> int:
        if not self.length:
            return len(tokens)
        positive, negative, score = self._width, 0, self.length
        for token in tokens:
            equal = self._masks.get(token, 0)
            combined = equal | negative
            zero = (((equal & positive) + positive) ^ positive) | combined
            plus = negative | ~(zero | positive)
            minus = positive & zero
            score += bool(plus & self._high) - bool(minus & self._high)
            plus, minus = (plus << 1) | 1, minus << 1
            positive = (minus | ~(zero | plus)) & self._width
            negative = (plus & zero) & self._width
        return score
