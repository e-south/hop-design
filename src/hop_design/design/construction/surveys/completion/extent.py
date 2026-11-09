"""Algebraic local stream extents, independent of admitted populations."""

from dataclasses import dataclass

from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain
from hop_design.kernel.construction.basal.programs import BasalPlacementFailure
from hop_design.kernel.construction.basal.sequence_index import BasalSequenceIndex
from hop_design.kernel.construction.foldback.domains import solve_foldback_sequence_domain
from hop_design.kernel.construction.foldback.solutions import FoldbackPlacementFailure
from hop_design.models.construction.request import LocalNeighborhoodRequest
from hop_design.models.construction.search import FoldbackGeometryDomain

from ...basal.traversal import iter_basal_work_units
from ...foldback.candidates import _payload_has_actionable_site
from ...foldback.traversal import iter_foldback_work_units
from ...overhead import foldback_overhead_levels


@dataclass(frozen=True)
class LocalExtent:
    """Largest canonical program stream, before reaction-stage admission."""

    parts: int
    work_units: int

    def partition(self, ordinal: int) -> dict[str, int]:
        if not 0 <= ordinal < self.parts:
            raise ValueError("Local part address lies outside its computed candidate extent.")
        return {"part_count": max(2, self.parts), "part_index": ordinal}


def local_extent(request: LocalNeighborhoodRequest) -> LocalExtent:
    """Count placement streams algebraically; never infer complete-route support."""
    largest, units = 0, 0
    if request.family.value == "foldback":
        assert isinstance(request.geometry_domain, FoldbackGeometryDomain)
        for level in foldback_overhead_levels(request.geometry_domain, request.search):
            for unit in iter_foldback_work_units(request, level=level):
                domain = solve_foldback_sequence_domain(
                    payload_sequence=unit.payload_sequence, target=unit.target, program=unit.program
                )
                count = (
                    1
                    if isinstance(domain, FoldbackPlacementFailure)
                    or _payload_has_actionable_site(unit)
                    else domain.precursor_cardinality
                )
                largest, units = max(largest, count), units + 1
    else:
        for overhead in range(request.search.max_retained_overhead_nt + 1):
            for basal_unit in iter_basal_work_units(request, retained_overhead_nt=overhead):
                basal_domain = solve_basal_sequence_domain(
                    payload_sequence=basal_unit.payload_sequence,
                    target=basal_unit.target,
                    endpoint=request.endpoint,
                    program=basal_unit.program,
                )
                count = (
                    1
                    if isinstance(basal_domain, BasalPlacementFailure)
                    else BasalSequenceIndex.create(basal_domain).cardinality
                )
                largest, units = max(largest, count), units + 1
    # Include empty parts too: aggregate coverage records every declared part,
    # rather than silently treating an algebraic cardinality as replay evidence.
    return LocalExtent(max(2, largest), units)
