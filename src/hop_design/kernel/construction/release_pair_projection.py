"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/release_pair_projection.py

Projects coupled contact assignments onto the two exposed end words.

Maintainer(s): HOP Design contributors
--------------------------------------------------------------------------------
"""

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
            output_masks[position] = tuple(
                reverse_complement_iupac(value) if base.complemented else value
                for value in masks[base.index]
            )
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
    hidden_cost = 0
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
        least = min(cost for _, _, cost in pairs)
        minimum_cost += least
        if minimum_cost > budget:
            return 0
        if source_index in groups or adapter_index in groups:
            contacts.append((source_index, adapter_index, pairs))
        else:
            # Each contact owns distinct source/adapter variables. If neither
            # is observed, a cheapest allowed pair is an existential witness;
            # more expensive hidden choices cannot admit another output word.
            hidden_cost += least
    budget = min(budget - hidden_cost, len(contacts))
    assignment_roots: dict[tuple[tuple[int, str], ...], int] = {}

    def assignments(values: dict[int, str]) -> int:
        # A hidden partner can affect contact cost without changing this output
        # mask. The visible contact factors below retain that cost. Roots belong
        # to this builder and are discarded with this call.
        key = tuple((variable, base) for variable, base in values.items() if variable in groups)
        if key not in assignment_roots:
            domains = [_BASES] * len(ends)
            for variable, base in key:
                for position, complemented in groups[variable]:
                    value = reverse_complement_iupac(base) if complemented else base
                    domains[position] = tuple(b for b in domains[position] if b == value)
            assignment_roots[key] = builder.from_domains(domains)
        return assignment_roots[key]

    for variable, positions in groups.items():
        # Independent masks are already present. Repeated observations still
        # need one shared assignment to preserve copies and complements.
        if len(positions) == 1:
            continue
        permitted = 0
        for base in masks[variable]:
            permitted = builder.union(permitted, assignments({variable: base}))
        admitted = builder.intersection(admitted, permitted)

    if not contacts:
        return admitted
    states = [admitted] + [0] * budget
    for source_index, adapter_index, pairs in contacts:
        factors = [0, 0]
        for source, adapter, cost in pairs:
            if cost > budget:
                continue
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
