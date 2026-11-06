"""Existentially project coupled contacts onto the two exposed end words."""

from collections import defaultdict

from hop_design.models.construction import BasalPairAllowance, BasalPairClass
from hop_design.models.construction.basal import derive_basal_pair_class
from hop_design.models.sequence import reverse_complement_iupac

from .basal.domains import BasalSequenceDomain
from .basal.programs import _adapter_domains
from .foldback.domains import SequenceExpression
from .sequence_sets import SequenceSetBuilder

_BASES = tuple("ACGT")


def project_end_pairs(
    domain: BasalSequenceDomain,
    masks: tuple[tuple[str, ...], ...],
    ends: SequenceExpression,
    builder: SequenceSetBuilder,
) -> int:
    """Preserve copy aliases, conditional pairing and the global mismatch budget.

    Input masks are independent placement constraints. Pair factors introduce
    dependencies explicitly; a source base is never independently combined with
    an incompatible adapter base. Bases absent from the output are existential.
    """
    groups: dict[int, list[tuple[int, bool]]] = defaultdict(list)
    output_masks = [_BASES] * len(ends)
    for position, base in enumerate(ends):
        if isinstance(base, str):
            output_masks[position] = (base,)
        else:
            groups[base.index].append((position, base.complemented))
    admitted = builder.from_domains(output_masks)
    budget = domain.target.max_noncanonical_pairs
    budget = (
        len(domain.source_arm_domains)
        if budget is None
        else min(budget, len(domain.source_arm_domains))
    )
    # Contact minima are a necessary lower bound, including hidden bases.
    # Passing it does not resolve correlations: the exact DP still follows.
    contacts = []
    pair_options: dict[
        tuple[
            tuple[str, ...], tuple[str, ...], BasalPairAllowance, tuple[str, ...], tuple[str, ...]
        ],
        tuple[tuple[str, str, int], ...],
    ] = {}
    minimum_cost = 0
    for position, constraint in enumerate(domain.target.pairing_constraints):
        source_index = domain.source_span.end.offset - 1 - position
        adapter_index = domain.adapter_span.start.offset + position
        # Positions retain their own factors and costs. Only the literal choices
        # for identical masks and contact permissions can be shared.
        key = (
            masks[source_index],
            masks[adapter_index],
            constraint.allowed_class,
            constraint.allowed_source_bases,
            constraint.allowed_adapter_bases,
        )
        pairs = pair_options.get(key)
        if pairs is None:
            pairs = tuple(
                (
                    source,
                    adapter,
                    int(derive_basal_pair_class(source, adapter) is not BasalPairClass.MATCH),
                )
                for source in masks[source_index]
                for adapter in masks[adapter_index]
                if adapter in _adapter_domains(source, constraint=constraint)
            )
            pair_options[key] = pairs
        if not pairs:
            return 0
        minimum_cost += min(cost for _, _, cost in pairs)
        if minimum_cost > budget:
            return 0
        contacts.append((source_index, adapter_index, pairs))
    assignment_roots: dict[tuple[tuple[int, str], ...], int] = {}

    def assignments(values: dict[int, str]) -> int:
        # Hidden bases still consume the pairing budget below, but cannot
        # change this output mask. Roots belong to this builder and are
        # discarded with this call; all pairing factors still run below.
        key = tuple((variable, base) for variable, base in values.items() if variable in groups)
        if key not in assignment_roots:
            domains = [_BASES] * len(ends)
            for variable, base in key:
                for position, complemented in groups[variable]:
                    value = reverse_complement_iupac(base) if complemented else base
                    domains[position] = tuple(b for b in domains[position] if b == value)
            assignment_roots[key] = builder.from_domains(domains)
        return assignment_roots[key]

    for variable in groups:
        permitted = 0
        for base in masks[variable]:
            permitted = builder.union(permitted, assignments({variable: base}))
        admitted = builder.intersection(admitted, permitted)

    states = [admitted] + [0] * budget
    for source_index, adapter_index, pairs in contacts:
        factors = [0, 0]
        for source, adapter, cost in pairs:
            factors[cost] = builder.union(
                factors[cost], assignments({source_index: source, adapter_index: adapter})
            )
        following = [0] * (budget + 1)
        for used, state in enumerate(states):
            for cost, factor in enumerate(factors):
                if used + cost <= budget:
                    following[used + cost] = builder.union(
                        following[used + cost], builder.intersection(state, factor)
                    )
        states = following
    result = 0
    for state in states:
        result = builder.union(result, state)
    return result
