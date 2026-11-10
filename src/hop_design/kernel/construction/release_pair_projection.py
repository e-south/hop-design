"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/release_pair_projection.py

Projects coupled contact assignments onto the two exposed end words.

Maintainer(s): HOP Design contributors
--------------------------------------------------------------------------------
"""

from collections import OrderedDict, defaultdict
from dataclasses import dataclass

from hop_design.models.construction import BasalPairAllowance, BasalPairClass
from hop_design.models.construction.basal import derive_basal_pair_class
from hop_design.models.construction.sequence_sets import MAX_SEQUENCE_VARIABLES, SequenceSet
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes

from .basal.domains import BasalSequenceDomain
from .basal.programs import _adapter_domains
from .foldback.domains import SequenceExpression
from .sequence_sets import SequenceSetBuilder

_BASES = tuple("ACGT")
_MAX_PROJECTIONS = 512
_MAX_PROJECTION_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class _ProjectionKey:
    masks: tuple[tuple[str, ...], ...]
    ends: SequenceExpression
    output_length: int
    source_end: int
    adapter_start: int
    source_arm_length: int
    noncanonical_budget: int | None
    constraints: tuple[tuple[int, BasalPairAllowance, tuple[str, ...], tuple[str, ...]], ...]


class EndPairProjectionCache:
    """Reuse exact output sets across domains within one discovery invocation.

    Placement and enzyme checks precede this calculation. Keys snapshot every
    input read by the projector; values contain immutable sets, never builder
    handles or failed/unfinished work. Retention is capped at 512 entries and
    8 MiB of serialized values, with bounded keys and Python overhead additional.
    """

    def __init__(self) -> None:
        self._entries: OrderedDict[_ProjectionKey, tuple[SequenceSet, int]] = OrderedDict()
        self._bytes = 0

    def project(
        self,
        domain: BasalSequenceDomain,
        masks: tuple[tuple[str, ...], ...],
        ends: SequenceExpression,
        builder: SequenceSetBuilder,
    ) -> int:
        builder._active()
        if any(
            length > MAX_SEQUENCE_VARIABLES
            for length in (len(masks), len(ends), len(domain.target.pairing_constraints))
        ):
            return project_end_pairs(domain, masks, ends, builder)
        key = _ProjectionKey(
            masks,
            ends,
            builder.length_nt,
            domain.source_span.end.offset,
            domain.adapter_span.start.offset,
            len(domain.source_arm_domains),
            domain.target.max_noncanonical_pairs,
            tuple(
                (
                    c.position_from_ligation,
                    c.allowed_class,
                    c.allowed_source_bases,
                    c.allowed_adapter_bases,
                )
                for c in domain.target.pairing_constraints
            ),
        )
        cached = self._entries.get(key)
        if cached is not None:
            root = builder.import_set(cached[0])
            self._entries.move_to_end(key)
            return root
        root = project_end_pairs(domain, masks, ends, builder)
        sequences = builder.freeze(root)
        size = len(canonical_json_bytes(sequences))
        if size <= _MAX_PROJECTION_BYTES:
            self._entries[key] = sequences, size
            self._bytes += size
            while len(self._entries) > _MAX_PROJECTIONS or self._bytes > _MAX_PROJECTION_BYTES:
                _, (_, removed) = self._entries.popitem(last=False)
                self._bytes -= removed
        return root


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
