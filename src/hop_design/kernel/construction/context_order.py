"""Prioritize source-compatible contexts without dropping any authored assignment."""

from dataclasses import dataclass

from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.kernel.construction.source_context import SourceContextPopulation
from hop_design.models.construction.sequence_sets import SequenceSet


@dataclass(frozen=True)
class SourceContextOrder:
    """Two disjoint exact sets whose union remains the entire authored domain."""

    preferred: SourceContextPopulation
    remaining: SequenceSet

    @classmethod
    def create(
        cls, preferred: SourceContextPopulation, *, max_decisions: int, max_operations: int
    ) -> "SourceContextOrder":
        builder = SequenceSetBuilder(
            length_nt=preferred.sequences.length_nt,
            max_nodes=max_decisions,
            max_operations=max_operations,
        )
        all_words = builder.from_iupac(preferred.authored_pattern)
        subset = builder.import_set(preferred.sequences)
        if builder.difference(subset, all_words) != 0:
            raise ValueError("Preferred contexts must remain within the authored domain.")
        remaining = builder.freeze(builder.difference(all_words, subset))
        return cls(preferred, remaining)

    def member_at(self, position: int) -> tuple[str, int]:
        count = self.preferred.sequences.cardinality
        if type(position) is not int or not 0 <= position < count + self.remaining.cardinality:
            raise ValueError("Context priority position is outside its authored domain.")
        if position < count:
            return self.preferred.member_at(position)
        word = self.remaining.member_at(position - count)
        return word, self.preferred.canonical_rank(word)

    def position(self, word: str) -> int:
        if self.preferred.sequences.contains(word):
            return self.preferred.sequences.rank_of(word)
        return self.preferred.sequences.cardinality + self.remaining.rank_of(word)
