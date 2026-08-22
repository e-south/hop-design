"""Pure IUPAC-domain expansion for basal-junction candidate pairs."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import product
from math import prod

from hop_design.models.discovery.basal_candidates import BasalCandidateSearchRequest
from hop_design.models.sequence import iupac_bases


def basal_candidate_domains(
    request: BasalCandidateSearchRequest,
) -> tuple[tuple[tuple[str, ...], ...], tuple[tuple[str, ...], ...]]:
    """Return deterministic exact-base domains for both declared arms."""
    left = tuple(tuple(sorted(iupac_bases(symbol))) for symbol in request.left_arm_template)
    right = tuple(tuple(sorted(iupac_bases(symbol))) for symbol in request.right_arm_template)
    return left, right


def basal_candidate_space_size(
    domains: tuple[tuple[tuple[str, ...], ...], tuple[tuple[str, ...], ...]],
) -> int:
    """Return exact arm-pair cardinality before candidate allocation."""
    left, right = domains
    return prod(len(domain) for domain in (*left, *right))


def enumerate_basal_candidate_pairs(
    domains: tuple[tuple[tuple[str, ...], ...], tuple[tuple[str, ...], ...]],
) -> Iterator[tuple[str, str]]:
    """Yield exact arm pairs in deterministic lexical domain order."""
    left_domains, right_domains = domains
    for left_bases in product(*left_domains):
        left_arm = "".join(left_bases)
        for right_bases in product(*right_domains):
            yield left_arm, "".join(right_bases)


__all__ = [
    "basal_candidate_domains",
    "basal_candidate_space_size",
    "enumerate_basal_candidate_pairs",
]
