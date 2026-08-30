"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/foldback/orientation.py

Mirrors exact foldback solutions across a duplex orientation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.foldback import FoldbackEnzymeBinding
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.physical import SiteOrientation, opposite_strand
from hop_design.models.sequence import reverse_complement_iupac

from .solutions import FoldbackSequenceSolution


def opposite_orientation(orientation: SiteOrientation) -> SiteOrientation:
    """Return the physical recognition orientation on the opposite strand."""
    return (
        SiteOrientation.REVERSE
        if orientation is SiteOrientation.FORWARD
        else SiteOrientation.FORWARD
    )


def mirror_binding(
    binding: FoldbackEnzymeBinding,
    *,
    source_nt: int,
) -> FoldbackEnzymeBinding:
    """Mirror one exact binding across a reverse-complemented source."""
    return FoldbackEnzymeBinding.create(
        enzyme_id=binding.enzyme_id,
        role=binding.role,
        strand=opposite_strand(binding.strand),
        recognition_span=Span(
            start=Boundary(offset=source_nt - binding.recognition_span.end.offset),
            end=Boundary(offset=source_nt - binding.recognition_span.start.offset),
        ),
        orientation=opposite_orientation(binding.orientation),
        reference_cut=(
            Boundary(offset=source_nt - binding.complement_cut.offset)
            if binding.complement_cut is not None
            else None
        ),
        complement_cut=(
            Boundary(offset=source_nt - binding.reference_cut.offset)
            if binding.reference_cut is not None
            else None
        ),
    )


def mirror_solution(solution: FoldbackSequenceSolution) -> FoldbackSequenceSolution:
    """Mirror one complete foldback solution without changing its final hairpin."""
    source_nt = len(solution.source_reference_sequence)
    return FoldbackSequenceSolution(
        source_reference_sequence=reverse_complement_iupac(solution.source_reference_sequence),
        retained_sequence=solution.retained_sequence,
        loop_sequence=solution.loop_sequence,
        foldback_arm_sequence=solution.foldback_arm_sequence,
        junction_boundary=source_nt - solution.junction_boundary,
        terminus_boundary=source_nt - solution.terminus_boundary,
        enzyme_bindings=tuple(
            mirror_binding(binding, source_nt=source_nt) for binding in solution.enzyme_bindings
        ),
    )


__all__ = ["mirror_solution", "opposite_orientation"]
