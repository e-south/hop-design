"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/overhead.py

Enumerates exact local geometry domains in retained-overhead order.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator

from hop_design.models.construction.search import (
    FoldbackGeometryDomain,
    FoldbackOverheadLevel,
    NeighborhoodSearchPlan,
)
from hop_design.models.construction.targets import FoldbackTarget


def iter_foldback_geometries(
    domain: FoldbackGeometryDomain, *, maximum: int
) -> Iterator[FoldbackTarget]:
    """Yield bounded geometries in overhead, displacement, cap, and arm order."""
    loop_lengths = domain.loop_lengths_nt or tuple(
        range(domain.minimum_loop_length_nt, maximum + 1)
    )
    allowed_arms = set(domain.annealing_arm_lengths_bp)
    for overhead in range(maximum + 1):
        for junction_offset in domain.junction_offsets_nt:
            if junction_offset > overhead // 2:
                break
            for loop_length in loop_lengths:
                paired = overhead - loop_length
                if paired < 0 or paired % 2:
                    continue
                arm_length = paired // 2
                if arm_length < max(domain.minimum_annealing_arm_length_bp, junction_offset):
                    continue
                if allowed_arms and arm_length not in allowed_arms:
                    continue
                words = (
                    tuple(word for word in domain.loop_sequences if len(word) == loop_length)
                    if domain.loop_sequences is not None
                    else (None,)
                )
                for word in words:
                    yield FoldbackTarget(
                        nick_strand=domain.nick_strand,
                        junction_offset_nt=junction_offset,
                        loop_length_nt=loop_length,
                        annealing_arm_length_bp=arm_length,
                        loop_sequence=word,
                    )


def foldback_overhead_levels(
    domain: FoldbackGeometryDomain,
    plan: NeighborhoodSearchPlan,
) -> tuple[FoldbackOverheadLevel, ...]:
    """Return every admissible foldback geometry grouped by exact overhead."""
    maximum = plan.max_retained_overhead_nt
    geometries_by_overhead: dict[int, list[FoldbackTarget]] = {
        overhead: [] for overhead in range(maximum + 1)
    }
    for target in iter_foldback_geometries(domain, maximum=maximum):
        overhead = target.loop_length_nt + 2 * target.annealing_arm_length_bp
        geometries_by_overhead[overhead].append(target)
    return tuple(
        FoldbackOverheadLevel(
            retained_overhead_nt=overhead,
            geometries=tuple(
                sorted(
                    geometries,
                    key=lambda item: (
                        item.junction_offset_nt,
                        item.loop_length_nt,
                        item.annealing_arm_length_bp,
                    ),
                )
            ),
        )
        for overhead, geometries in geometries_by_overhead.items()
    )


__all__ = ["foldback_overhead_levels"]
