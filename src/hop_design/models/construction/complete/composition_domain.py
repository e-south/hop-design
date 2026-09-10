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

from .source_preparation.policy import ConstrainedSourceSsdnaPolicy, SourceSsdnaPolicy


def source_context_count(policy: SourceSsdnaPolicy) -> int:
    """Count upstream assignments without allocating their sequence strings."""
    if isinstance(policy, ConstrainedSourceSsdnaPolicy):
        return prod(len(iupac_bases(symbol)) for symbol in policy.upstream_sequence_spec)
    return 1


def source_contexts(policy: SourceSsdnaPolicy) -> Iterator[str | None]:
    """Yield exact upstream assignments in A/C/G/T positional order."""
    if isinstance(policy, ConstrainedSourceSsdnaPolicy):
        domains = tuple(
            tuple(sorted(iupac_bases(symbol))) for symbol in policy.upstream_sequence_spec
        )
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
    if sequence is None or len(sequence) != len(policy.upstream_sequence_spec):
        raise ValueError("A constrained source requires one exact upstream assignment.")
    if any(
        base not in iupac_bases(symbol)
        for base, symbol in zip(sequence, policy.upstream_sequence_spec, strict=True)
    ):
        raise ValueError("Upstream assignment must belong to its declared sequence domain.")
