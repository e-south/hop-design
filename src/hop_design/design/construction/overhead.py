"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/overhead.py

Enumerates exact local geometry domains in retained-overhead order.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.search import (
    FoldbackGeometryDomain,
    FoldbackOverheadLevel,
    NeighborhoodSearchPlan,
)
from hop_design.models.construction.targets import FoldbackTarget


def foldback_overhead_levels(
    domain: FoldbackGeometryDomain,
    plan: NeighborhoodSearchPlan,
) -> tuple[FoldbackOverheadLevel, ...]:
    """Return every admissible foldback geometry grouped by exact overhead."""
    maximum = plan.max_retained_overhead_nt
    loop_lengths = domain.loop_lengths_nt or tuple(
        range(domain.minimum_loop_length_nt, maximum + 1)
    )
    arm_lengths = domain.annealing_arm_lengths_bp or tuple(
        range(domain.minimum_annealing_arm_length_bp, maximum // 2 + 1)
    )
    geometries_by_overhead: dict[int, list[FoldbackTarget]] = {
        overhead: [] for overhead in range(maximum + 1)
    }
    for junction_offset in domain.junction_offsets_nt:
        for loop_length in loop_lengths:
            for arm_length in arm_lengths:
                retained_overhead = loop_length + 2 * arm_length
                if retained_overhead > maximum or junction_offset > arm_length:
                    continue
                geometries_by_overhead[retained_overhead].append(
                    FoldbackTarget(
                        nick_strand=domain.nick_strand,
                        junction_offset_nt=junction_offset,
                        loop_length_nt=loop_length,
                        annealing_arm_length_bp=arm_length,
                    )
                )
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
