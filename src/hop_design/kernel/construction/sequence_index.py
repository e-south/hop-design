"""Direct addressing of finite lexicographic sequence products."""

from math import prod

from hop_design.models.construction.sequence_domain import SequenceDomainPartition


def assignment_at(domains: tuple[tuple[str, ...], ...], rank: int) -> tuple[str, ...]:
    """Unrank without generating earlier assignments; the last position varies fastest."""
    if type(rank) is not int or not 0 <= rank < prod(map(len, domains)):
        raise ValueError("Sequence rank lies outside its finite domain.")
    result = []
    for domain in reversed(domains):
        rank, digit = divmod(rank, len(domain))
        result.append(domain[digit])
    return tuple(reversed(result))


def candidate_range(
    cardinality: int,
    *,
    start: int,
    stop: int | None,
    partition: SequenceDomainPartition | None = None,
) -> range:
    """Intersect an absolute candidate window with an optional existing modulo part."""
    if (
        type(start) is not int
        or start < 0
        or (stop is not None and (type(stop) is not int or stop < start))
    ):
        raise ValueError("Candidate window requires nonnegative integer start <= stop.")
    end = cardinality if stop is None else min(stop, cardinality)
    if partition is None:
        return range(start, end)
    first = start + (partition.part_index - start) % partition.part_count
    return range(first, end, partition.part_count)
