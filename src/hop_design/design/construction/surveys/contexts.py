"""Recover an exact permitted upstream context without generating its predecessors."""

from hop_design.kernel.construction.sequence_index import assignment_at
from hop_design.models.construction.complete.composition_domain import source_context_count
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    SourceSsdnaPolicy,
    UpstreamSequenceLengthRange,
)
from hop_design.models.sequence import iupac_bases

from .coordinates import interleaved_at


def _length_populations(policy: SourceSsdnaPolicy, rank: int) -> tuple[int, ...]:
    count = source_context_count(policy)
    if type(rank) is not int or not 0 <= rank < count:
        raise ValueError("Source context rank lies outside its declared domain.")
    if isinstance(policy, ConstrainedSourceSsdnaPolicy):
        specification = policy.upstream_sequence_spec
        if isinstance(specification, UpstreamSequenceLengthRange):
            alphabet = len(iupac_bases(specification.base_spec))
            return tuple(
                alphabet**length
                for length in range(specification.min_length_nt, specification.max_length_nt + 1)
            )
    return (count,)


def source_context_rank_at(policy: SourceSsdnaPolicy, position: int) -> int:
    """Map fair traversal position to the unchanged length-first molecular address."""
    sizes = _length_populations(policy, position)
    length, member = interleaved_at(sizes, position)
    return sum(sizes[:length]) + member


def source_context_position(policy: SourceSsdnaPolicy, rank: int) -> int:
    """Recover traversal position without enumerating context words or predecessors."""
    sizes = _length_populations(policy, rank)
    for length, size in enumerate(sizes):
        if rank < size:
            return sum(min(n, rank) for n in sizes) + sum(n > rank for n in sizes[:length])
        rank -= size
    raise AssertionError("Validated source context rank lost its length population.")


def source_context_at(policy: SourceSsdnaPolicy, rank: int) -> str | None:
    """Use the ordinary composition order: length first, then lexicographic bases."""
    if type(rank) is not int or not 0 <= rank < source_context_count(policy):
        raise ValueError("Source context rank lies outside its declared domain.")
    if not isinstance(policy, ConstrainedSourceSsdnaPolicy):
        return None
    specification = policy.upstream_sequence_spec
    if isinstance(specification, UpstreamSequenceLengthRange):
        bases = tuple(sorted(iupac_bases(specification.base_spec)))
        for length in range(specification.min_length_nt, specification.max_length_nt + 1):
            count = len(bases) ** length
            if rank < count:
                return "".join(assignment_at((bases,) * length, rank))
            rank -= count
        raise AssertionError("Validated source context rank was not addressed.")
    domains = tuple(tuple(sorted(iupac_bases(symbol))) for symbol in specification)
    return "".join(assignment_at(domains, rank))
