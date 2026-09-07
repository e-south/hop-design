"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/foldback/traversal.py

Traverses exact foldback geometry, strand, payload, and enzyme work units.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from hop_design.kernel.construction.foldback.programs import (
    FoldbackProgramCandidate,
    iter_foldback_programs,
)
from hop_design.models.construction import (
    FoldbackTarget,
    LocalNeighborhoodRequest,
    NickStrandSelection,
)
from hop_design.models.construction.search import FoldbackOverheadLevel
from hop_design.models.physical import Strand

from ..neighborhood_accounting import payload_assignments


@dataclass(frozen=True, slots=True)
class FoldbackWorkUnit:
    """One exact local query before sequence placement or route evaluation."""

    target: FoldbackTarget
    payload_sequence: str
    program: FoldbackProgramCandidate


def iter_foldback_work_units(
    request: LocalNeighborhoodRequest, *, level: FoldbackOverheadLevel
) -> Iterator[FoldbackWorkUnit]:
    """Yield geometry-major units without buffering the payload cross product."""
    for geometry in level.geometries:
        exact_geometries = (
            tuple(geometry.model_copy(update={"nick_strand": strand}) for strand in Strand)
            if geometry.nick_strand is NickStrandSelection.ANY
            else (geometry,)
        )
        for target in exact_geometries:
            programs = iter_foldback_programs(request.enzyme_provisioning, target=target)
            if not programs:
                continue
            for payload_sequence in payload_assignments(request):
                for program in programs:
                    yield FoldbackWorkUnit(
                        target=target, payload_sequence=payload_sequence, program=program
                    )
