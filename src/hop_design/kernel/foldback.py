"""Pure foldback pairing and arm-enumeration mechanics."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import combinations, product
from math import comb

from hop_design.models.junction import JunctionPairObservation, classify_literal_pair
from hop_design.models.sequence import reverse_complement_iupac

_DNA_BASES = ("A", "C", "G", "T")


@dataclass(frozen=True)
class PairingSummary:
    """Antiparallel pair calls with explicit Watson-Crick-only run metrics."""

    non_watson_crick_positions: tuple[int, ...]
    terminal_watson_crick_bp: int
    max_uninterrupted_watson_crick_bp: int
    pairs: tuple[JunctionPairObservation, ...]


def summarize_pairing(
    *, retained_sequence: str, foldback_arm: str, arm_start: int
) -> PairingSummary:
    """Measure non-Watson-Crick positions and Watson-Crick runs."""
    aligned_arm = "" if not foldback_arm else reverse_complement_iupac(foldback_arm)
    matched_mask = tuple(
        retained_base == aligned_base
        for retained_base, aligned_base in zip(retained_sequence, aligned_arm, strict=True)
    )
    non_watson_crick_positions = tuple(
        index for index, matched in enumerate(matched_mask) if not matched
    )

    terminal_watson_crick_bp = 0
    for matched in matched_mask:
        if not matched:
            break
        terminal_watson_crick_bp += 1

    max_uninterrupted_watson_crick_bp = 0
    current_run = 0
    for matched in matched_mask:
        current_run = current_run + 1 if matched else 0
        max_uninterrupted_watson_crick_bp = max(max_uninterrupted_watson_crick_bp, current_run)

    arm_end = arm_start + len(foldback_arm)
    pairs = tuple(
        JunctionPairObservation(
            left_index=index,
            right_index=arm_end - 1 - index,
            left_base=retained_sequence[index],
            right_base=foldback_arm[-1 - index],
            kind=classify_literal_pair(
                left_base=retained_sequence[index],
                right_base=foldback_arm[-1 - index],
            ),
        )
        for index, matched in enumerate(matched_mask)
    )
    return PairingSummary(
        non_watson_crick_positions=non_watson_crick_positions,
        terminal_watson_crick_bp=terminal_watson_crick_bp,
        max_uninterrupted_watson_crick_bp=max_uninterrupted_watson_crick_bp,
        pairs=pairs,
    )


def foldback_arm_candidate_count(*, paired_bp: int, max_non_watson_crick_pairs: int) -> int:
    """Return the exact size of an arm space before enumeration."""
    capped_mismatches = min(paired_bp, max_non_watson_crick_pairs)
    return sum(comb(paired_bp, count) * (3**count) for count in range(capped_mismatches + 1))


def enumerate_foldback_arms(
    retained_sequence: str, *, max_non_watson_crick_pairs: int
) -> Iterator[str]:
    """Yield the exact arm first, then non-Watson-Crick tiers in deterministic order."""
    exact_arm = reverse_complement_iupac(retained_sequence)
    yield exact_arm
    for non_watson_crick_count in range(1, min(len(exact_arm), max_non_watson_crick_pairs) + 1):
        for positions in combinations(range(len(exact_arm)), non_watson_crick_count):
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
