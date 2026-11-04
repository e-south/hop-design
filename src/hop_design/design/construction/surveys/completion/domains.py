"""Address context groups and their exact completions without expanding handles."""

from collections.abc import Callable
from dataclasses import dataclass
from math import prod

from hop_design.kernel.construction.sequence_order import SeededSequenceOrder
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.kernel.construction.source_context import (
    SourceContextCompletionGroups,
    SourceContextPopulation,
)
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    SourceSsdnaPolicy,
    UpstreamSequenceLengthRange,
)
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits
from hop_design.models.sequence import iupac_bases

from ..coordinates import interleaved_at
from .group_preference import preferred_group_index


@dataclass(frozen=True)
class ContextCompletionDomain:
    """One length/protected sequence; preference never removes permitted completions."""

    pattern: str | None
    canonical_origin: int
    suffix: str
    preferred: SequenceSet | None
    remaining: SequenceSet | None
    known: SequenceSet | None = None
    handle_seed: str = ""
    max_order_states: int = 1_000_000

    @property
    def ordered_domains(self) -> tuple[SequenceSet, ...]:
        return tuple(d for d in (self.known, self.preferred, self.remaining) if d is not None)

    @property
    def length_nt(self) -> int | None:
        return None if self.pattern is None else len(self.pattern)

    @property
    def completion_count(self) -> int:
        if self.remaining is None:
            return 1
        return sum(domain.cardinality for domain in self.ordered_domains)

    def member_at(self, position: int) -> tuple[str | None, int]:
        if type(position) is not int or not 0 <= position < self.completion_count:
            raise ValueError("Completion address lies outside its exact group domain.")
        if self.remaining is None:
            return None, 0
        assert self.pattern is not None
        for domain in self.ordered_domains:
            if position < domain.cardinality:
                word = SeededSequenceOrder(
                    domain, self.handle_seed, self.max_order_states
                ).member_at(position)
                return word, SourceContextPopulation(
                    domain, self.pattern, self.canonical_origin
                ).canonical_rank(word)
            position -= domain.cardinality
        raise AssertionError("Completion domains disagree with their total cardinality.")

    def next_unexcluded(
        self, position: int, patterns: tuple[str, ...], *, limits: SequenceSpaceLimits
    ) -> int | None:
        """Seek in the original preference order without visiting excluded words."""
        if not 0 <= position <= self.completion_count:
            raise ValueError("Completion seek lies outside its exact group domain.")
        if position == self.completion_count:
            return None
        if not patterns:
            return position
        if self.pattern is None:
            raise ValueError("Exact-material policies cannot acquire context exclusions.")
        builder = SequenceSetBuilder(
            length_nt=len(self.pattern),
            max_nodes=limits.max_decisions,
            max_operations=limits.max_set_operations,
        )
        forbidden = 0
        for pattern in patterns:
            forbidden = builder.union(forbidden, builder.from_iupac(pattern))
        origin = 0
        for domain in self.ordered_domains:
            if not domain.cardinality:
                continue
            if position < origin + domain.cardinality:
                admitted = builder.freeze(builder.difference(builder.import_set(domain), forbidden))
                budget = min(self.max_order_states, limits.max_set_operations)
                order = SeededSequenceOrder(domain, self.handle_seed, budget)
                admitted_order = SeededSequenceOrder(admitted, self.handle_seed, budget)
                lower_key = order.key(order.member_at(max(0, position - origin)))
                lo, hi = 0, admitted.cardinality
                while lo < hi:
                    mid = (lo + hi) // 2
                    if admitted_order.key(admitted_order.member_at(mid)) < lower_key:
                        lo = mid + 1
                    else:
                        hi = mid
                if lo < admitted.cardinality:
                    return origin + order.rank_of(admitted_order.member_at(lo))
            origin += domain.cardinality
        return None


@dataclass(frozen=True)
class ContextCompletionPlan:
    """Fair length/group traversal with unchanged canonical full-word addresses.

    ``protected_suffix_nt`` must come from a separately validated molecular
    dependency bound. This class cannot establish that changing a base preserves
    the required molecular features or that a nonempty group has a complete construction.
    """

    populations: tuple[SourceContextCompletionGroups, ...]
    patterns: tuple[str, ...]
    origins: tuple[int, ...]
    limits: SequenceSpaceLimits
    preferred_contexts: tuple[str, ...] = ()
    handle_seed: str = ""

    @classmethod
    def create(
        cls,
        policy: SourceSsdnaPolicy,
        *,
        protected_suffix_nt: int,
        limits: SequenceSpaceLimits,
        condition: Callable[[str], SequenceSet | None] | None = None,
        preferred_contexts: tuple[str, ...] = (),
        handle_seed: str = "",
    ) -> "ContextCompletionPlan":
        if type(protected_suffix_nt) is not int or protected_suffix_nt < 0:
            raise ValueError("Protected suffix must be a nonnegative integer count.")
        if not isinstance(policy, ConstrainedSourceSsdnaPolicy):
            if preferred_contexts or handle_seed:
                raise ValueError("An exact-material policy cannot acquire context preferences.")
            return cls((), (), (), limits)
        spec = policy.upstream_sequence_spec
        patterns = (
            tuple(spec.base_spec * n for n in range(spec.min_length_nt, spec.max_length_nt + 1))
            if isinstance(spec, UpstreamSequenceLengthRange)
            else (spec,)
        )
        populations, origins = [], []
        origin = 0
        for pattern in patterns:
            builder = SequenceSetBuilder(
                length_nt=len(pattern),
                max_nodes=limits.max_decisions,
                max_operations=limits.max_set_operations,
            )
            sequences = builder.freeze(builder.from_iupac(pattern))
            authored_count = sequences.cardinality
            admitted = None if condition is None else condition(pattern)
            if admitted is not None:
                sequences = builder.freeze(
                    builder.intersection(
                        builder.import_set(sequences), builder.import_set(admitted)
                    )
                )
            populations.append(
                SourceContextCompletionGroups.create(
                    sequences,
                    protected_suffix_nt=min(protected_suffix_nt, len(pattern)),
                    max_decisions=limits.max_decisions,
                    max_operations=limits.max_set_operations,
                )
            )
            origins.append(origin)
            origin += authored_count
        return cls(
            tuple(populations), patterns, tuple(origins), limits, preferred_contexts, handle_seed
        )

    @property
    def group_count(self) -> int:
        return sum(p.group_count for p in self.populations) if self.populations else 1

    @property
    def raw_context_count(self) -> int:
        return (
            sum(prod(len(iupac_bases(b)) for b in p) for p in self.patterns) if self.patterns else 1
        )

    @property
    def admitted_context_count(self) -> int:
        return sum(p.sequences.cardinality for p in self.populations) if self.populations else 1

    def group_at(
        self, position: int, *, preferred: SequenceSet | None = None
    ) -> ContextCompletionDomain:
        if type(position) is not int or not 0 <= position < self.group_count:
            raise ValueError("Group address lies outside the exact completion plan.")
        if not self.populations:
            if preferred is not None:
                raise ValueError("An authored exact-material policy cannot acquire new contexts.")
            return ContextCompletionDomain(None, 0, "", None, None)
        length, group = interleaved_at(tuple(p.group_count for p in self.populations), position)
        population = self.populations[length]
        if preferred is not None:
            group = preferred_group_index(population, group, preferred, limits=self.limits)
        domain = population.completions(group)
        suffix = population.suffix_at(group)
        # A full known word can belong only to its own protected suffix group.
        # Avoid constructing decision diagrams for unrelated groups.
        known_words = tuple(
            word
            for word in self.preferred_contexts
            if len(word) == domain.length_nt and word.endswith(suffix)
        )
        remaining = domain
        known = None
        if preferred is not None or known_words:
            builder = SequenceSetBuilder(
                length_nt=domain.length_nt,
                max_nodes=self.limits.max_decisions,
                max_operations=self.limits.max_set_operations,
            )
            whole = builder.import_set(domain)
            chosen_known = 0
            for word in known_words:
                chosen_known = builder.union(chosen_known, builder.from_iupac(word))
            chosen_known = builder.intersection(whole, chosen_known)
            if known_words:
                known = builder.freeze(chosen_known)
            whole = builder.difference(whole, chosen_known)
            chosen = (
                0
                if preferred is None
                else builder.intersection(whole, builder.import_set(preferred))
            )
            remaining = builder.freeze(builder.difference(whole, chosen))
            if preferred is not None:
                preferred = builder.freeze(chosen)
        return ContextCompletionDomain(
            self.patterns[length],
            self.origins[length],
            suffix,
            preferred,
            remaining,
            known,
            self.handle_seed[: domain.length_nt - len(suffix)],
            self.limits.max_set_operations,
        )
