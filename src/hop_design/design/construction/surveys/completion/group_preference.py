"""Order consequential groups by exact conditional preference, without pruning."""

from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.kernel.construction.source_context import SourceContextCompletionGroups
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits


def preferred_group_index(
    population: SourceContextCompletionGroups,
    group: int,
    preferred: SequenceSet,
    *,
    limits: SequenceSpaceLimits,
) -> int:
    """Return the canonical group at a preferred-first traversal position.

    Project the intersection with permitted full words before ordering suffixes.
    A suffix with both preferred and nonpreferred completions occurs only once.
    Every other permitted suffix follows; this is not an exclusion certificate.
    """
    if population.protected_suffix_nt == 0:
        population.suffix_at(group)
        return group
    whole, first, later = _suffix_order(population, preferred, limits)
    word = (
        first.member_at(group)
        if group < first.cardinality
        else later.member_at(group - first.cardinality)
    )
    return whole.rank_of(word)


def preferred_group_position(
    population: SourceContextCompletionGroups,
    group: int,
    preferred: SequenceSet,
    *,
    limits: SequenceSpaceLimits,
) -> int:
    """Locate a canonical suffix directly, without traversing earlier groups."""
    word = population.suffix_at(group)
    if population.protected_suffix_nt == 0:
        return group
    _, first, later = _suffix_order(population, preferred, limits)
    try:
        return first.rank_of(word)
    except ValueError:
        return first.cardinality + later.rank_of(word)


def _suffix_order(
    population: SourceContextCompletionGroups,
    preferred: SequenceSet,
    limits: SequenceSpaceLimits,
) -> tuple[SequenceSet, SequenceSet, SequenceSet]:
    count = population.protected_suffix_nt
    full = population.sequences
    builder = SequenceSetBuilder(
        length_nt=full.length_nt,
        max_nodes=limits.max_decisions,
        max_operations=limits.max_set_operations,
    )
    permitted = builder.freeze(
        builder.intersection(builder.import_set(full), builder.import_set(preferred))
    )
    suffixes = SequenceSetBuilder(
        length_nt=count,
        max_nodes=limits.max_decisions,
        max_operations=limits.max_set_operations,
    )
    whole = suffixes.project_window(full, start=full.length_nt - count, end=full.length_nt)
    first = suffixes.freeze(
        suffixes.project_window(permitted, start=full.length_nt - count, end=full.length_nt)
    )
    later = suffixes.freeze(suffixes.difference(whole, suffixes.import_set(first)))
    return suffixes.freeze(whole), first, later
