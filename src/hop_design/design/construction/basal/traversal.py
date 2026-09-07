"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal/traversal.py

Traverses exact basal geometry, strand, payload, and enzyme work units.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from hop_design.kernel.construction.basal import (
    basal_retained_overhead_nt,
    iter_basal_programs,
)
from hop_design.kernel.construction.basal.programs import BasalProgramCandidate
from hop_design.models.construction import (
    BasalGeometryDomain,
    BasalTarget,
    LocalNeighborhoodRequest,
    NickStrandSelection,
)
from hop_design.models.physical import Strand

from ..neighborhood_accounting import payload_assignments


@dataclass(frozen=True, slots=True)
class BasalWorkUnit:
    """One exact local query with any required future-release obligation."""

    target: BasalTarget
    payload_sequence: str
    program: BasalProgramCandidate


def iter_basal_work_units(
    request: LocalNeighborhoodRequest, *, retained_overhead_nt: int
) -> Iterator[BasalWorkUnit]:
    """Yield offset-major units belonging to one retained-overhead level."""
    if not isinstance(request.geometry_domain, BasalGeometryDomain):
        raise ValueError("Basal traversal requires a basal geometry domain.")
    for geometry in request.geometry_domain.exact_targets():
        exact_targets = (
            tuple(geometry.model_copy(update={"nick_strand": strand}) for strand in Strand)
            if geometry.nick_strand is NickStrandSelection.ANY
            else (geometry,)
        )
        for target in exact_targets:
            programs = tuple(
                program
                for program in iter_basal_programs(
                    request.enzyme_provisioning, target=target, endpoint=request.endpoint
                )
                if basal_retained_overhead_nt(
                    target=target, endpoint=request.endpoint, program=program
                )
                == retained_overhead_nt
            )
            if not programs:
                continue
            for payload_sequence in payload_assignments(request):
                for program in programs:
                    yield BasalWorkUnit(
                        target=target, payload_sequence=payload_sequence, program=program
                    )
