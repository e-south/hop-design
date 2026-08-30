"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal/states.py

Discovers exact basal construction neighborhoods.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.kernel.construction.basal import (
    BasalProgramCandidate,
    BasalSequenceSolution,
)
from hop_design.models.construction.basal import (
    BasalAdapterAnnealedComplex,
    BasalAdapterLigatedProduct,
    BasalPcrCopyState,
    BasalRestrictionProduct,
    derive_cohesive_end,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.molecular_replay import (
    observe_pair,
    reindex_lineage,
)
from hop_design.models.molecular_state import (
    CovalentBond,
    EndChemistry,
    LineageStrand,
    MolecularStrand,
    StrandEnd,
)
from hop_design.models.reactions import (
    ReactionMolecule,
    ReactionOperation,
    ReactionProgram,
    ReactionStage,
    ReactionState,
)
from hop_design.models.sequence import reverse_complement_iupac

from .reactions import _declared, _strand


def _pcr_states(
    solution: BasalSequenceSolution,
) -> tuple[
    BasalAdapterAnnealedComplex | None,
    BasalAdapterLigatedProduct | None,
    BasalPcrCopyState | None,
]:
    profile = solution.pairing_profile
    adapter_sequence = solution.adapter_sequence
    if profile is None or adapter_sequence is None:
        return None, None, None
    source = _strand(
        strand_id="source-fragment",
        sequence=solution.source_precursor_sequence,
        origin_id="source-precursor",
        origin_strand=LineageStrand.PRIMARY,
    )
    adapter = _strand(
        strand_id="ligation-adapter",
        sequence=adapter_sequence,
        origin_id="ligation-adapter",
        origin_strand=LineageStrand.PRIMARY,
    )
    pairs = tuple(
        observe_pair(
            left_strand_id=source.strand_id,
            right_strand_id=adapter.strand_id,
            left_index=profile.source_span.start.offset + pair.source_index,
            right_index=pair.adapter_index,
            left_base=pair.source_base,
            right_base=pair.adapter_base,
        )
        for pair in profile.pairs
    )
    annealed = BasalAdapterAnnealedComplex(
        source_strand=source,
        adapter_strand=adapter,
        pairs=pairs,
    )
    bond = CovalentBond(
        upstream_strand_id=source.strand_id,
        upstream_end=StrandEnd.THREE_PRIME,
        downstream_strand_id=adapter.strand_id,
        downstream_end=StrandEnd.FIVE_PRIME,
    )
    ligated_sequence = source.sequence + adapter.sequence
    ligated_strand = MolecularStrand(
        strand_id="adapter-ligated-product",
        sequence=ligated_sequence,
        five_prime_end=source.five_prime_end,
        three_prime_end=adapter.three_prime_end,
        lineage=reindex_lineage((source.lineage, adapter.lineage)),
    )
    adapter_ligated = BasalAdapterLigatedProduct(
        source_strand=source,
        adapter_strand=adapter,
        bond=bond,
        strand=ligated_strand,
    )
    top = MolecularStrand(
        strand_id="hairpin-pcr-top",
        sequence=ligated_sequence,
        five_prime_end=ligated_strand.five_prime_end,
        three_prime_end=ligated_strand.three_prime_end,
        lineage=ligated_strand.lineage,
    )
    bottom = _strand(
        strand_id="hairpin-pcr-bottom",
        sequence=reverse_complement_iupac(ligated_sequence),
        origin_id=ligated_strand.strand_id,
        origin_strand=LineageStrand.COMPLEMENTARY,
    )
    return (
        annealed,
        adapter_ligated,
        BasalPcrCopyState(top_strand=top, bottom_strand=bottom),
    )


def _restriction_product(
    solution: BasalSequenceSolution, duplex: BasalPcrCopyState
) -> BasalRestrictionProduct:
    end_bindings = tuple(
        binding for binding in solution.enzyme_bindings if binding.role is EnzymeRole.END_GENERATION
    )
    if len(end_bindings) != 2:
        raise ValueError("end-generation-binding-count")
    left, right = sorted(end_bindings, key=lambda item: item.recognition_span.start.offset)
    if None in (left.reference_cut, left.complement_cut, right.reference_cut, right.complement_cut):
        raise ValueError("end-generation-cut-model")
    if (
        left.reference_cut is None
        or left.complement_cut is None
        or right.reference_cut is None
        or right.complement_cut is None
    ):
        raise RuntimeError("Validated end-generation cuts were lost.")
    top_start = left.reference_cut.offset
    top_end = right.reference_cut.offset
    bottom_start = left.complement_cut.offset
    bottom_end = right.complement_cut.offset
    if not (top_start < top_end and bottom_start < bottom_end):
        raise ValueError("end-generation-facing-sites")
    primary_parent_span = Span(
        start=Boundary(offset=top_start),
        end=Boundary(offset=top_end),
    )
    parent_length = len(duplex.bottom_strand.sequence)
    complementary_parent_span = Span(
        start=Boundary(offset=parent_length - bottom_end),
        end=Boundary(offset=parent_length - bottom_start),
    )
    primary = MolecularStrand(
        strand_id="clone-primary",
        sequence=duplex.top_strand.sequence[top_start:top_end],
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=reindex_lineage((duplex.top_strand.lineage[top_start:top_end],)),
    )
    complementary = MolecularStrand(
        strand_id="clone-complementary",
        sequence=duplex.bottom_strand.sequence[
            complementary_parent_span.start.offset : complementary_parent_span.end.offset
        ],
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=reindex_lineage(
            (
                duplex.bottom_strand.lineage[
                    complementary_parent_span.start.offset : complementary_parent_span.end.offset
                ],
            )
        ),
    )
    ends = (
        derive_cohesive_end(
            side="left",
            top_sequence=duplex.top_strand.sequence,
            binding=left,
            primary_strand_id=primary.strand_id,
            complementary_strand_id=complementary.strand_id,
        ),
        derive_cohesive_end(
            side="right",
            top_sequence=duplex.top_strand.sequence,
            binding=right,
            primary_strand_id=primary.strand_id,
            complementary_strand_id=complementary.strand_id,
        ),
    )
    return BasalRestrictionProduct(
        binding_ids=(left.binding_id, right.binding_id),
        primary_parent_span=primary_parent_span,
        complementary_parent_span=complementary_parent_span,
        primary_strand=primary,
        complementary_strand=complementary,
        cohesive_ends=ends,
    )


def _end_program(
    duplex: BasalPcrCopyState,
    product: BasalRestrictionProduct,
    solution: BasalSequenceSolution,
    route: BasalProgramCandidate,
) -> ReactionProgram:
    if route.end_enzyme is None:
        raise ValueError("end-generation-unavailable")
    bindings = tuple(
        binding for binding in solution.enzyme_bindings if binding.role is EnzymeRole.END_GENERATION
    )
    pre = ReactionState(
        state_id="hairpin-pcr-duplex",
        molecules=(
            ReactionMolecule(
                molecule_id="hairpin-pcr",
                reference_sequence_5prime=duplex.top_strand.sequence,
                complement_sequence_5prime=duplex.bottom_strand.sequence,
            ),
        ),
    )
    post = ReactionState(
        state_id="clone-ready-product",
        molecules=(
            ReactionMolecule(
                molecule_id="clone-primary",
                reference_sequence_5prime=product.primary_strand.sequence,
                complement_sequence_5prime=None,
            ),
            ReactionMolecule(
                molecule_id="clone-complementary",
                reference_sequence_5prime=product.complementary_strand.sequence,
                complement_sequence_5prime=None,
            ),
        ),
    )
    operations = tuple(
        ReactionOperation(
            operation_id=f"end-generation-{side}",
            enzyme_id=route.end_enzyme.enzyme_id,
            role=EnzymeRole.END_GENERATION,
            molecule_id="hairpin-pcr",
            intended_binding=_declared(binding),
        )
        for side, binding in zip(("left", "right"), bindings, strict=True)
    )
    return ReactionProgram(
        program_id="clone-end-generation",
        states=(pre, post),
        stages=(
            ReactionStage(
                stage_id="clone-end-generation",
                pre_state_id=pre.state_id,
                post_state_id=post.state_id,
                operations=operations,
            ),
        ),
    )
