"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/composition_domain.py

Defines canonical local-junction and upstream-sequence composition domains.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import product
from math import prod

from hop_design.models.sequence import iupac_bases

from .source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    SourceSsdnaPolicy,
    UpstreamSequenceLengthRange,
)


def source_context_count(policy: SourceSsdnaPolicy) -> int:
    """Count upstream assignments without allocating their sequence strings."""
    if isinstance(policy, ConstrainedSourceSsdnaPolicy):
        specification = policy.upstream_sequence_spec
        if isinstance(specification, UpstreamSequenceLengthRange):
            base_count = len(iupac_bases(specification.base_spec))
            if base_count == 1:
                return specification.max_length_nt - specification.min_length_nt + 1
            count: int = (
                base_count ** (specification.max_length_nt + 1)
                - base_count**specification.min_length_nt
            ) // (base_count - 1)
            return count
        return prod(len(iupac_bases(symbol)) for symbol in specification)
    return 1


def source_contexts(policy: SourceSsdnaPolicy) -> Iterator[str | None]:
    """Yield exact upstream assignments by length, then A/C/G/T positional order."""
    if isinstance(policy, ConstrainedSourceSsdnaPolicy):
        specification = policy.upstream_sequence_spec
        if isinstance(specification, UpstreamSequenceLengthRange):
            bases = tuple(sorted(iupac_bases(specification.base_spec)))
            for length in range(specification.min_length_nt, specification.max_length_nt + 1):
                for assignment in product(bases, repeat=length):
                    yield "".join(assignment)
        else:
            domains = tuple(tuple(sorted(iupac_bases(symbol))) for symbol in specification)
            for assignment in product(*domains):
                yield "".join(assignment)
    else:
        yield None


def composition_domain[F, B](
    foldbacks: tuple[F, ...], basals: tuple[B, ...], policy: SourceSsdnaPolicy
) -> Iterator[tuple[F, B, str | None]]:
    """Yield local pairs then upstream assignments without materializing the context space."""
    for foldback, basal in product(foldbacks, basals):
        for sequence in source_contexts(policy):
            yield foldback, basal, sequence


def validate_source_context(policy: SourceSsdnaPolicy, sequence: str | None) -> None:
    """Require the exact context to belong to its declared source policy."""
    if not isinstance(policy, ConstrainedSourceSsdnaPolicy):
        if sequence is not None:
            raise ValueError("An upstream assignment requires a constrained source policy.")
        return
    specification = policy.upstream_sequence_spec
    if sequence is None:
        raise ValueError("A constrained source requires one exact upstream assignment.")
    if isinstance(specification, UpstreamSequenceLengthRange):
        if not specification.min_length_nt <= len(sequence) <= specification.max_length_nt:
            raise ValueError("A constrained source requires one exact upstream assignment.")
        if any(base not in iupac_bases(specification.base_spec) for base in sequence):
            raise ValueError("Upstream assignment must belong to its declared sequence domain.")
        return
    if len(sequence) != len(specification):
        raise ValueError("A constrained source requires one exact upstream assignment.")
    if any(
        base not in iupac_bases(symbol)
        for base, symbol in zip(sequence, specification, strict=True)
    ):
        raise ValueError("Upstream assignment must belong to its declared sequence domain.")
