"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/foldback/solutions.py

Defines exact foldback sequence-placement outcomes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction.foldback import FoldbackEnzymeBinding


@dataclass(frozen=True, slots=True)
class FoldbackSequenceSolution:
    """One exact source and its intended enzyme bindings."""

    source_reference_sequence: str
    retained_sequence: str
    loop_sequence: str
    foldback_arm_sequence: str
    junction_boundary: int
    terminus_boundary: int
    enzyme_bindings: tuple[FoldbackEnzymeBinding, ...]


@dataclass(frozen=True, slots=True)
class FoldbackPlacementFailure:
    """One stable reason a concrete program cannot realize a geometry."""

    code: str


__all__ = ["FoldbackPlacementFailure", "FoldbackSequenceSolution"]
