"""Compact joint basal choices: admitted source decisions and conditional adapters."""

from collections.abc import Callable, Iterator
from functools import cache
from math import prod

from hop_design.models.construction import BasalPairClass
from hop_design.models.construction.basal import derive_basal_pair_class
from hop_design.models.construction.sequence_sets import BASE_ORDER, SequenceSet

from ..sequence_index import assignment_at
from ..sequence_sets import SequenceSetLimitError
from .programs import BasalPlacementFailure, BasalSequenceSolution
from .sequence_index import BasalSequenceIndex


def _cost(source: str, adapter: str) -> int:
    return int(derive_basal_pair_class(source, adapter) is not BasalPairClass.MATCH)


def _adapter_counts(
    choices: tuple[tuple[str, ...], ...], paired_source: str
) -> Callable[[int, int], int]:
    @cache
    def remaining(position: int, budget: int) -> int:
        if budget < 0:
            return 0
        if position == len(choices):
            return 1
        return sum(
            remaining(position + 1, budget - _cost(paired_source[position], base))
            for base in choices[position]
        )

    return remaining


class BasalSequencePopulation:
    """Count and recover joint members without expanding source or adapter strings.

    Source decisions retain correlations from reaction admission. Adapter choices
    remain conditional on each source base and the global noncanonical-pair cap.
    This is a local population, never a complete-construction certificate.
    """

    def __init__(self, index: BasalSequenceIndex, sources: SequenceSet, *, max_operations: int):
        if not index.adapter_present or sources.length_nt != index.domain.adapter_span.start.offset:
            raise ValueError("Basal population requires the full source and a paired adapter.")
        if type(max_operations) is not int or max_operations < 1:
            raise ValueError("Basal population requires a positive operation budget.")
        self.index, self.sources = index, sources
        self._limit = max_operations
        self._counts: dict[tuple[int, int, int], int] = {}
        self._masks = index.source_domains()
        self._pair_positions = dict(zip(index.domain.variable_indexes, index.choices, strict=True))
        budget = index.domain.target.max_noncanonical_pairs
        self._budget = len(index.choices) if budget is None else budget
        self._tail = tuple(i for i in index.domain.unresolved_indexes if i >= sources.length_nt)
        self._tail_domains = tuple(index.domain.base_domains[i] for i in self._tail)
        self._tail_count = prod(map(len, self._tail_domains))
        self.cardinality = self._count(0, sources.root, self._budget) * self._tail_count

    def _child(self, node: int, position: int, base: str) -> int:
        if node >= 2 and self.sources.decisions[node - 2].position_nt == position:
            return self.sources.decisions[node - 2].branches[BASE_ORDER.index(base)]
        return node

    def _weights(self, position: int, base: str) -> tuple[tuple[int, int], ...]:
        if base not in self._masks[position]:
            return ()
        if position not in self._pair_positions:
            return ((0, 1),)
        adapters = dict(self._pair_positions[position])[base]
        counts = [0, 0]
        for adapter in adapters:
            counts[_cost(base, adapter)] += 1
        return tuple((cost, count) for cost, count in enumerate(counts) if count)

    def _count(self, position: int, node: int, budget: int) -> int:
        if not node or budget < 0:
            return 0
        if position == self.sources.length_nt:
            return 1
        key = (position, node, budget)
        if key not in self._counts:
            if len(self._counts) >= self._limit:
                raise SequenceSetLimitError("Basal joint-population operation budget exhausted.")
            # Reserve the state before recursion so the limit includes active work.
            self._counts[key] = 0
            self._counts[key] = sum(
                weight * self._count(position + 1, self._child(node, position, base), budget - cost)
                for base in BASE_ORDER
                for cost, weight in self._weights(position, base)
            )
        return self._counts[key]

    def _source_branches(
        self, position: int, node: int, prefix: dict[int, int]
    ) -> Iterator[tuple[str, int, dict[int, int], int]]:
        """Count each next source base with its still-conditional adapter choices."""
        for base in BASE_ORDER:
            following: dict[int, int] = {}
            for used, ways in prefix.items():
                for cost, count in self._weights(position, base):
                    if used + cost <= self._budget:
                        following[used + cost] = following.get(used + cost, 0) + ways * count
            child = self._child(node, position, base)
            count = self._tail_count * sum(
                ways * self._count(position + 1, child, self._budget - used)
                for used, ways in following.items()
            )
            yield base, child, following, count

    def _adapter_order(self, source: str) -> tuple[str, tuple[tuple[str, ...], ...]]:
        domain = self.index.domain
        arm = source[domain.source_span.start.offset : domain.source_span.end.offset]
        choices = tuple(
            dict(alternatives)[base]
            for base, alternatives in zip(arm, self.index.choices, strict=True)
        )[::-1]
        return arm[::-1], choices

    def member_at(self, rank: int) -> BasalSequenceSolution:
        """Full-source lexicographic order, then adapter and extra context order."""
        if type(rank) is not int or not 0 <= rank < self.cardinality:
            raise ValueError("Basal population rank lies outside admitted joint members.")
        node = self.sources.root
        prefix = {0: 1}
        source = []
        for position in range(self.sources.length_nt):
            for base, child, next_prefix, count in self._source_branches(position, node, prefix):
                if rank < count:
                    source.append(base)
                    prefix, node = next_prefix, child
                    break
                rank -= count
        source_word = "".join(source)
        domain = self.index.domain
        paired_source, choices = self._adapter_order(source_word)
        remaining = _adapter_counts(choices, paired_source)

        adapter_rank, tail_rank = divmod(rank, self._tail_count)
        budget = self._budget
        bases = list(source_word) + [d[0] for d in domain.base_domains[self.sources.length_nt :]]
        for position, alternatives in enumerate(choices):
            for base in alternatives:
                cost = _cost(paired_source[position], base)
                count = remaining(position + 1, budget - cost)
                if adapter_rank < count:
                    bases[domain.adapter_span.start.offset + position] = base
                    budget -= cost
                    break
                adapter_rank -= count
        for index, base in zip(
            self._tail, assignment_at(self._tail_domains, tail_rank), strict=True
        ):
            bases[index] = base
        result = domain.materialize(source_word, "".join(bases[self.sources.length_nt :]))
        if isinstance(result, BasalPlacementFailure):
            raise ValueError("Admitted basal joint member failed exact materialization.")
        return result

    def rank_of(self, solution: BasalSequenceSolution) -> int:
        """Locate one admitted joint member without visiting preceding sequences."""
        domain = self.index.domain
        source, adapter = solution.source_precursor_sequence, solution.adapter_sequence
        if (
            adapter is None
            or domain.materialize(source, adapter) != solution
            or not self.sources.contains(source)
        ):
            raise ValueError("Basal solution does not belong to this admitted population.")
        rank, node, prefix = 0, self.sources.root, {0: 1}
        for position, selected in enumerate(source):
            for base, child, next_prefix, count in self._source_branches(position, node, prefix):
                if base == selected:
                    prefix, node = next_prefix, child
                    break
                rank += count
        paired_source, choices = self._adapter_order(source)
        remaining = _adapter_counts(choices, paired_source)

        adapter_rank, budget = 0, self._budget
        for position, alternatives in enumerate(choices):
            for base in alternatives:
                cost = _cost(paired_source[position], base)
                if base == adapter[position]:
                    budget -= cost
                    break
                adapter_rank += remaining(position + 1, budget - cost)
        tail_rank = 0
        sequence = source + adapter
        for index, alternatives in zip(self._tail, self._tail_domains, strict=True):
            tail_rank = tail_rank * len(alternatives) + alternatives.index(sequence[index])
        return rank + adapter_rank * self._tail_count + tail_rank
