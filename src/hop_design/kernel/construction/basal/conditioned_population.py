"""A disjoint restriction of joint basal choices with original raw addresses."""

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import replace

from hop_design.models.construction.sequence_sets import (
    BASE_ORDER,
    SequenceSet,
    SequenceSpaceLimits,
)

from ..sequence_sets import SequenceSetLimitError
from .programs import BasalSequenceSolution
from .sequence_index import BasalSequenceIndex
from .sequence_population import BasalSequencePopulation


def _boxes(sequences: SequenceSet, *, maximum: int) -> Iterator[tuple[tuple[str, ...], ...]]:
    """Visit disjoint decision paths, grouping equal branches rather than words."""
    masks = [tuple(BASE_ORDER)] * sequences.length_nt
    visits = 0

    def visit(node: int) -> Iterator[tuple[tuple[str, ...], ...]]:
        nonlocal visits
        visits += 1
        if visits > maximum:
            raise SequenceSetLimitError("Basal endpoint decision-path budget exhausted.")
        if node == 0:
            return
        if node == 1:
            yield tuple(masks)
            return
        decision = sequences.decisions[node - 2]
        grouped: dict[int, list[str]] = defaultdict(list)
        for base, child in zip(BASE_ORDER, decision.branches, strict=True):
            if child:
                grouped[child].append(base)
        previous = masks[decision.position_nt]
        for child, bases in sorted(grouped.items()):
            masks[decision.position_nt] = tuple(bases)
            yield from visit(child)
        masks[decision.position_nt] = previous

    yield from visit(sequences.root)


class ConditionedBasalPopulation:
    """Keep sequence/material identity independent from admitted candidate order."""

    def __init__(
        self, original: BasalSequencePopulation, permitted: SequenceSet, limits: SequenceSpaceLimits
    ):
        self.index = original.index
        domain = original.index.domain
        if permitted.length_nt != len(domain.base_domains):
            raise ValueError("Endpoint restriction must cover the complete local variable frame.")
        parts = []
        for box in _boxes(permitted, maximum=limits.max_set_operations):
            masks = tuple(
                tuple(b for b in old if b in permitted_bases)
                for old, permitted_bases in zip(domain.base_domains, box, strict=True)
            )
            if any(not values for values in masks):
                continue
            narrowed = replace(
                domain,
                base_domains=masks,
                source_arm_domains=tuple(
                    tuple(base for base in old if base in masks[i])
                    for i, old in zip(
                        domain.variable_indexes, domain.source_arm_domains, strict=True
                    )
                ),
            )
            subset = BasalSequencePopulation(
                BasalSequenceIndex.create(narrowed),
                original.sources,
                max_operations=limits.max_set_operations,
            )
            if subset.cardinality:
                parts.append(subset)
        self._parts = tuple(parts)
        self.cardinality = sum(p.cardinality for p in parts)
        if self.cardinality > original.cardinality:
            raise ValueError("Endpoint conditioning cannot enlarge a local population.")

    def member_at(self, rank: int) -> BasalSequenceSolution:
        if type(rank) is not int or not 0 <= rank < self.cardinality:
            raise ValueError("Basal endpoint address lies outside the conditioned population.")
        for part in self._parts:
            if rank < part.cardinality:
                return part.member_at(rank)
            rank -= part.cardinality
        raise AssertionError("A valid conditioned address resolves to a disjoint part.")

    def rank_of(self, solution: BasalSequenceSolution) -> int:
        """Locate a member in disjoint conditioned-part order, not its original rank."""
        origin = 0
        for part in self._parts:
            try:
                return origin + part.rank_of(solution)
            except ValueError:
                origin += part.cardinality
        raise ValueError("Basal solution does not belong to this conditioned population.")
