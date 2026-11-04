"""Address every exact four-base end pair independently of search execution."""

from itertools import product

from pydantic import Field, field_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import normalize_dna_sequence

FOUR_BASE_WORDS = tuple("".join(bases) for bases in product("ACGT", repeat=4))


class InterfaceTargetDomain(HopModel):
    """Explicit Cartesian word permission; omitted sides contain all 256 words.

    Words are read 5-prime to 3-prime on their own protruding strands. Polarity,
    orientation, placement and molecular constraints belong to the survey
    request. An address is a target, never a feasibility assertion.
    """

    left_words: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=256)
    right_words: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=256)

    @field_validator("left_words", "right_words")
    @classmethod
    def exact_words(cls, values: tuple[str, ...] | None) -> tuple[str, ...] | None:
        if values is None:
            return None
        words = tuple(normalize_dna_sequence(word, allow_degenerate=False) for word in values)
        if any(len(word) != 4 for word in words):
            raise ValueError("Interface survey words must contain exactly four bases.")
        if len(set(words)) != len(words):
            raise ValueError("Interface survey words must not repeat.")
        return tuple(sorted(words))

    @property
    def left_count(self) -> int:
        return len(self.left_words or FOUR_BASE_WORDS)

    @property
    def right_count(self) -> int:
        return len(self.right_words or FOUR_BASE_WORDS)

    @property
    def pair_count(self) -> int:
        return self.left_count * self.right_count

    def _require_address(self, value: int) -> None:
        if type(value) is not int or not 0 <= value < self.pair_count:
            raise ValueError("Interface target address must be an integer inside the domain.")

    def pair_at(self, ordinal: int) -> tuple[str, str]:
        """Return one pair in canonical left-major order without allocating the roster."""
        self._require_address(ordinal)
        left, right = divmod(ordinal, self.right_count)
        return (self.left_words or FOUR_BASE_WORDS)[left], (self.right_words or FOUR_BASE_WORDS)[
            right
        ]

    def coverage_ordinal(self, rank: int) -> int:
        """Interleave marginal words, then visit every pair exactly once.

        This establishes deterministic initial scheduling, not complete-witness
        coverage: the executor must retain and revisit unresolved targets.
        """
        self._require_address(rank)
        round_index, left = divmod(rank, self.left_count)
        right = (round_index + left) % self.right_count
        return left * self.right_count + right

    def coverage_rank(self, ordinal: int) -> int:
        """Recover traversal position from the stable canonical pair address."""
        self._require_address(ordinal)
        left, right = divmod(ordinal, self.right_count)
        return ((right - left) % self.right_count) * self.left_count + left
