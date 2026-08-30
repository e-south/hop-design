"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/clone/digest.py

Derives exact staggered strands, pairings, ends, and design projection after digestion.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction.basal import (
    BasalEnzymeBinding,
    BasalRealizationRecord,
    derive_cohesive_end,
)
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.coordinates import Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import (
    CohesiveEnd,
    EndChemistry,
    MolecularStrand,
    SequenceProjection,
    StrandPairObservation,
)
from hop_design.models.physical import classify_literal_pair
from hop_design.models.sequence import reverse_complement_iupac

from ..state import ConstructionState, ConstructionStatePhase
from .geometry import (
    CloneEndGenerationError,
    derive_clone_cut_geometry,
    lift_clone_end_bindings,
    validate_clone_binding_definitions,
)


@dataclass(frozen=True, slots=True)
class CloneDigest:
    """Pure derived facts for one complete clone-ready digest."""

    bindings: tuple[BasalEnzymeBinding, BasalEnzymeBinding]
    parent_length: int
    primary_parent_span: Span
    complementary_parent_span: Span
    strands: tuple[MolecularStrand, MolecularStrand]
    pairings: tuple[StrandPairObservation, ...]
    cohesive_ends: tuple[CohesiveEnd, CohesiveEnd]
    encoding_projection: SequenceProjection


def _product_strand(
    *,
    strand_id: str,
    parent: MolecularStrand,
    span: Span,
) -> MolecularStrand:
    start = span.start.offset
    end = span.end.offset
    if start >= end or end > len(parent.sequence):
        raise CloneEndGenerationError("Clone digest cuts must retain nonempty exact strands.")
    return MolecularStrand(
        strand_id=strand_id,
        sequence=parent.sequence[start:end],
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=tuple(
            item.model_copy(update={"product_index": index})
            for index, item in enumerate(parent.lineage[start:end])
        ),
    )


def _clone_pairings(
    *,
    top: MolecularStrand,
    bottom: MolecularStrand,
    primary_span: Span,
    complementary_span: Span,
    parent_length: int,
) -> tuple[StrandPairObservation, ...]:
    bottom_reference_start = parent_length - complementary_span.end.offset
    bottom_reference_end = parent_length - complementary_span.start.offset
    overlap_start = max(primary_span.start.offset, bottom_reference_start)
    overlap_end = min(primary_span.end.offset, bottom_reference_end)
    if overlap_start >= overlap_end:
        raise CloneEndGenerationError("Clone digest products must retain one paired overlap.")
    records = []
    for parent_top_index in range(overlap_start, overlap_end):
        top_index = parent_top_index - primary_span.start.offset
        parent_bottom_index = parent_length - 1 - parent_top_index
        bottom_index = parent_bottom_index - complementary_span.start.offset
        left_base = top.sequence[top_index]
        right_base = bottom.sequence[bottom_index]
        records.append(
            StrandPairObservation(
                left_strand_id=top.strand_id,
                right_strand_id=bottom.strand_id,
                left_index=top_index,
                right_index=bottom_index,
                left_base=left_base,
                right_base=right_base,
                kind=classify_literal_pair(left_base=left_base, right_base=right_base),
            )
        )
    return tuple(records)


def derive_clone_digest(
    *,
    basal: BasalRealizationRecord,
    foldback: FoldbackLocalRealization,
    pcr_state: ConstructionState,
    design_sequence: str,
    design_digest: str,
) -> CloneDigest:
    """Derive exact clone strands, pairings, ends, and design-union projection."""
    if (
        pcr_state.phase is not ConstructionStatePhase.HAIRPIN_PCR_DUPLEX
        or len(pcr_state.molecules) != 2
    ):
        raise CloneEndGenerationError("Clone digestion requires one exact PCR duplex state.")
    top_parent, bottom_parent = pcr_state.molecules
    if bottom_parent.sequence != reverse_complement_iupac(top_parent.sequence):
        raise CloneEndGenerationError("Clone digestion requires exact PCR complementarity.")
    parent_length = len(bottom_parent.sequence)
    bindings = lift_clone_end_bindings(basal=basal, foldback=foldback)
    validate_clone_binding_definitions(
        bindings=bindings,
        basal=basal,
        sequence=top_parent.sequence,
    )
    geometry = derive_clone_cut_geometry(
        bindings=bindings,
        parent_length=parent_length,
        template_sequence=top_parent.sequence,
        design_sequence=design_sequence,
    )
    primary = _product_strand(
        strand_id="complete-clone-primary",
        parent=top_parent,
        span=geometry.primary_parent_span,
    )
    complementary = _product_strand(
        strand_id="complete-clone-complementary",
        parent=bottom_parent,
        span=geometry.complementary_parent_span,
    )
    pairings = _clone_pairings(
        top=primary,
        bottom=complementary,
        primary_span=geometry.primary_parent_span,
        complementary_span=geometry.complementary_parent_span,
        parent_length=parent_length,
    )
    left, right = bindings
    cohesive_ends = (
        derive_cohesive_end(
            side="left",
            top_sequence=top_parent.sequence,
            binding=left,
            primary_strand_id=primary.strand_id,
            complementary_strand_id=complementary.strand_id,
        ),
        derive_cohesive_end(
            side="right",
            top_sequence=top_parent.sequence,
            binding=right,
            primary_strand_id=primary.strand_id,
            complementary_strand_id=complementary.strand_id,
        ),
    )
    projection = SequenceProjection(
        sequence=design_sequence,
        sequence_digest=design_digest,
        source_span=geometry.encoding_span,
        orientation=BindingOrientation.SAME_5TO3,
    )
    return CloneDigest(
        bindings=bindings,
        parent_length=parent_length,
        primary_parent_span=geometry.primary_parent_span,
        complementary_parent_span=geometry.complementary_parent_span,
        strands=(primary, complementary),
        pairings=pairings,
        cohesive_ends=cohesive_ends,
        encoding_projection=projection,
    )


__all__ = ["CloneDigest", "derive_clone_digest"]
