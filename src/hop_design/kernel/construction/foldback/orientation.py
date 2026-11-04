"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/foldback/orientation.py

Places and mirrors exact foldback enzyme bindings across duplex orientations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.foldback import FoldbackEnzymeBinding
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import CharacterizedEnzyme, EnzymeClass, EnzymeRole
from hop_design.models.physical import SiteOrientation, Strand, opposite_strand
from hop_design.models.sequence import reverse_complement_iupac

from .solutions import FoldbackPlacementFailure, FoldbackSequenceSolution


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


def oriented_pattern(enzyme: CharacterizedEnzyme, orientation: SiteOrientation) -> str:
    """Read the enzyme recognition pattern in the requested source orientation."""
    if orientation is SiteOrientation.FORWARD:
        return enzyme.recognition_pattern
    return reverse_complement_iupac(enzyme.recognition_pattern)


def _oriented_cuts(
    enzyme: CharacterizedEnzyme,
    *,
    orientation: SiteOrientation,
    site_start: int,
) -> tuple[int | None, int | None]:
    if orientation is SiteOrientation.FORWARD:
        reference_offset = enzyme.cut_offset_reference_strand
        complement_offset = enzyme.cut_offset_complement_strand
    elif enzyme.enzyme_class is EnzymeClass.NICKASE:
        reference_offset = None
        complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
    else:
        complement_native = enzyme.cut_offset_complement_strand
        if complement_native is None:
            raise ValueError("Duplex restriction enzymes require both strand cuts.")
        reference_offset = enzyme.recognition_length - complement_native
        complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
    return (
        site_start + reference_offset if reference_offset is not None else None,
        site_start + complement_offset if complement_offset is not None else None,
    )


def place_binding(
    enzyme: CharacterizedEnzyme,
    *,
    role: EnzymeRole,
    orientation: SiteOrientation,
    controlled_strand: Strand,
    controlled_boundary: int,
) -> FoldbackEnzymeBinding | FoldbackPlacementFailure | None:
    """Place recognition and cuts from one controlled strand boundary."""
    if orientation is SiteOrientation.FORWARD:
        controlled_offset = (
            enzyme.cut_offset_reference_strand
            if controlled_strand is Strand.TOP
            else enzyme.cut_offset_complement_strand
        )
    elif enzyme.enzyme_class is EnzymeClass.NICKASE:
        controlled_offset = (
            None
            if controlled_strand is Strand.TOP
            else enzyme.recognition_length - enzyme.cut_offset_reference_strand
        )
    else:
        complement_native = enzyme.cut_offset_complement_strand
        if complement_native is None:
            return None
        controlled_offset = (
            enzyme.recognition_length - complement_native
            if controlled_strand is Strand.TOP
            else enzyme.recognition_length - enzyme.cut_offset_reference_strand
        )
    if controlled_offset is None:
        return None
    site_start = controlled_boundary - controlled_offset
    if site_start < 0:
        return FoldbackPlacementFailure(
            code=f"{role.value.replace('_', '-')}-recognition-before-source"
        )
    reference_cut, complement_cut = _oriented_cuts(
        enzyme,
        orientation=orientation,
        site_start=site_start,
    )
    if any(cut is not None and cut < 0 for cut in (reference_cut, complement_cut)):
        return FoldbackPlacementFailure(code=f"{role.value.replace('_', '-')}-cut-before-source")
    return FoldbackEnzymeBinding.create(
        enzyme_id=enzyme.enzyme_id,
        role=role,
        strand=controlled_strand,
        recognition_span=Span(
            start=Boundary(offset=site_start),
            end=Boundary(offset=site_start + enzyme.recognition_length),
        ),
        orientation=orientation,
        reference_cut=(Boundary(offset=reference_cut) if reference_cut is not None else None),
        complement_cut=(Boundary(offset=complement_cut) if complement_cut is not None else None),
    )


__all__ = ["mirror_solution", "opposite_orientation", "oriented_pattern", "place_binding"]
