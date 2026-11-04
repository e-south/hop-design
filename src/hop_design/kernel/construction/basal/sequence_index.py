"""Direct basal source/adapter addressing with the existing canonical stream order."""

from dataclasses import dataclass
from math import prod

from ..sequence_index import assignment_at
from .domains import BasalSequenceDomain
from .programs import BasalPlacementFailure, BasalSequenceSolution, _adapter_domains


@dataclass(frozen=True, slots=True)
class BasalSequenceIndex:
    """Weighted source words, then adapter words, then unresolved context words."""

    domain: BasalSequenceDomain
    choices: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]
    unresolved: tuple[tuple[str, ...], ...]
    suffix_weights: tuple[int, ...]
    adapter_present: bool

    @classmethod
    def create(cls, domain: BasalSequenceDomain) -> "BasalSequenceIndex":
        arm_nt = len(domain.source_arm_domains)
        ends = dict(domain.adapter_end_bases)
        has_adapter = domain.adapter_span.start != domain.adapter_span.end
        choices = []
        for source_position, source_bases in enumerate(domain.source_arm_domains):
            position = arm_nt - 1 - source_position
            candidates = []
            for source_base in source_bases:
                adapters = (
                    tuple(
                        base
                        for base in _adapter_domains(
                            source_base, constraint=domain.target.pairing_constraints[position]
                        )
                        if base in domain.base_domains[domain.adapter_span.start.offset + position]
                        and (position not in ends or base == ends[position])
                    )
                    if has_adapter
                    else ("",)
                )
                if adapters:
                    candidates.append((source_base, adapters))
            choices.append(tuple(candidates))
        suffix = [1]
        for alternatives in reversed(choices):
            suffix.append(suffix[-1] * sum(len(adapters) for _, adapters in alternatives))
        return cls(
            domain,
            tuple(choices),
            tuple(domain.base_domains[i] for i in domain.unresolved_indexes),
            tuple(reversed(suffix)),
            has_adapter,
        )

    @property
    def cardinality(self) -> int:
        return self.suffix_weights[0] * prod(map(len, self.unresolved))

    def source_domains(self) -> tuple[tuple[str, ...], ...]:
        """Source masks with at least one locally permitted adapter at each pair."""
        domain = self.domain
        masks: list[tuple[str, ...]] = [
            (bases[0],) for bases in domain.base_domains[: domain.adapter_span.start.offset]
        ]
        for index in domain.unresolved_indexes:
            if index < len(masks):
                masks[index] = domain.base_domains[index]
        for index, alternatives in zip(domain.variable_indexes, self.choices, strict=True):
            masks[index] = tuple(base for base, _ in alternatives)
        return tuple(masks)

    def rank_of(self, solution: BasalSequenceSolution) -> int:
        """Address an admitted member in the original source/adapter/context stream."""
        source, adapter = solution.source_precursor_sequence, solution.adapter_sequence
        if self.domain.materialize(source, adapter) != solution:
            raise ValueError("Basal solution does not belong to this placement domain.")
        unresolved_count = prod(map(len, self.unresolved))
        rank, prefix = 0, 1
        adapters = []
        for position, (index, choices) in enumerate(
            zip(self.domain.variable_indexes, self.choices, strict=True)
        ):
            for base, permitted in choices:
                if base == source[index]:
                    adapters.append(permitted)
                    prefix *= len(permitted)
                    break
                rank += (
                    prefix * len(permitted) * self.suffix_weights[position + 1] * unresolved_count
                )
        adapter_rank = 0
        if self.adapter_present:
            assert adapter is not None
            for base, permitted in zip(adapter[: len(adapters)], reversed(adapters), strict=True):
                adapter_rank = adapter_rank * len(permitted) + permitted.index(base)
        context_rank = 0
        sequence = source + (adapter or "")
        for index, permitted in zip(self.domain.unresolved_indexes, self.unresolved, strict=True):
            context_rank = context_rank * len(permitted) + permitted.index(sequence[index])
        return rank + adapter_rank * unresolved_count + context_rank

    def member_at(self, rank: int) -> BasalSequenceSolution | BasalPlacementFailure:
        if type(rank) is not int or not 0 <= rank < self.cardinality:
            raise ValueError("Basal sequence rank lies outside its finite domain.")
        unresolved_count = prod(map(len, self.unresolved))
        source_bases, adapter_domains = [], []
        prefix_weight = 1
        for position, choices in enumerate(self.choices):
            for source, adapters in choices:
                count = (
                    prefix_weight
                    * len(adapters)
                    * self.suffix_weights[position + 1]
                    * unresolved_count
                )
                if rank >= count:
                    rank -= count
                    continue
                source_bases.append(source)
                adapter_domains.append(adapters)
                prefix_weight *= len(adapters)
                break
        adapter_rank, unresolved_rank = divmod(rank, unresolved_count)
        adapter = (
            assignment_at(tuple(reversed(adapter_domains)), adapter_rank)
            if self.adapter_present
            else ()
        )
        bases = [values[0] for values in self.domain.base_domains]
        for index, base in zip(self.domain.variable_indexes, source_bases, strict=True):
            bases[index] = base
        for index, base in enumerate(adapter, start=self.domain.adapter_span.start.offset):
            bases[index] = base
        for index, base in zip(
            self.domain.unresolved_indexes,
            assignment_at(self.unresolved, unresolved_rank),
            strict=True,
        ):
            bases[index] = base
        complete = "".join(bases)
        boundary = self.domain.adapter_span.start.offset
        return self.domain.materialize(
            complete[:boundary], complete[boundary:] if self.adapter_present else None
        )
