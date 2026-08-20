"""Pure foldback pairing and arm-enumeration mechanics."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import combinations, product
from math import comb

from hop_design.models.junction import JunctionPairKind, JunctionPairObservation
from hop_design.models.sequence import reverse_complement_iupac

_DNA_BASES = ("A", "C", "G", "T")


@dataclass(frozen=True)
class PairingSummary:
    """Internal value returned by pure antiparallel pairing analysis."""

    mismatch_positions: tuple[int, ...]
    terminal_paired_bp: int
    max_uninterrupted_paired_bp: int
    pairs: tuple[JunctionPairObservation, ...]


def summarize_pairing(
    *, retained_sequence: str, foldback_arm: str, arm_start: int
) -> PairingSummary:
    """Measure reverse-oriented complement pairing in retained-tract coordinates."""
    aligned_arm = reverse_complement_iupac(foldback_arm)
    matched_mask = tuple(
        retained_base == aligned_base
        for retained_base, aligned_base in zip(retained_sequence, aligned_arm, strict=True)
    )
    mismatch_positions = tuple(index for index, matched in enumerate(matched_mask) if not matched)

    terminal_paired_bp = 0
    for matched in matched_mask:
        if not matched:
            break
        terminal_paired_bp += 1

    max_uninterrupted_paired_bp = 0
    current_run = 0
    for matched in matched_mask:
        current_run = current_run + 1 if matched else 0
        max_uninterrupted_paired_bp = max(max_uninterrupted_paired_bp, current_run)

    arm_end = arm_start + len(foldback_arm)
    pairs = tuple(
        JunctionPairObservation(
            left_index=index,
            right_index=arm_end - 1 - index,
            left_base=retained_sequence[index],
            right_base=foldback_arm[-1 - index],
            kind=(JunctionPairKind.WATSON_CRICK if matched else JunctionPairKind.HARD_MISMATCH),
        )
        for index, matched in enumerate(matched_mask)
    )
    return PairingSummary(
        mismatch_positions=mismatch_positions,
        terminal_paired_bp=terminal_paired_bp,
        max_uninterrupted_paired_bp=max_uninterrupted_paired_bp,
        pairs=pairs,
    )


def foldback_arm_candidate_count(*, paired_bp: int, max_mismatches: int) -> int:
    """Return the exact size of an arm space before enumeration."""
    capped_mismatches = min(paired_bp, max_mismatches)
    return sum(comb(paired_bp, count) * (3**count) for count in range(capped_mismatches + 1))


def enumerate_foldback_arms(retained_sequence: str, *, max_mismatches: int) -> Iterator[str]:
    """Yield the exact arm first, then mismatch tiers in deterministic order."""
    exact_arm = reverse_complement_iupac(retained_sequence)
    yield exact_arm
    for mismatch_count in range(1, min(len(exact_arm), max_mismatches) + 1):
        for positions in combinations(range(len(exact_arm)), mismatch_count):
            replacement_sets = tuple(
                tuple(base for base in _DNA_BASES if base != exact_arm[position])
                for position in positions
            )
            for replacements in product(*replacement_sets):
                candidate = list(exact_arm)
                for position, replacement in zip(positions, replacements, strict=True):
                    candidate[position] = replacement
                yield "".join(candidate)


__all__ = [
    "PairingSummary",
    "enumerate_foldback_arms",
    "foldback_arm_candidate_count",
    "summarize_pairing",
]
