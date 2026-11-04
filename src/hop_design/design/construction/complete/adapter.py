"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/pcr.py

Materializes one exact basal-open hairpin PCR construction endpoint.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.complete import (
    AdapterAnnealingAuthority,
    AdapterLigationAuthority,
    ConstructionBondState,
    ConstructionProgram,
    ConstructionState,
    ConstructionStatePhase,
    ExactConstructionMaterial,
    MaterialUse,
)
from hop_design.models.construction.complete.evaluation import CombinationEvaluation
from hop_design.models.construction.complete.evaluation_inputs import (
    derive_linear_source_embedding,
)
from hop_design.models.construction.complete.pcr.pairing import complete_adapter_pairing
from hop_design.models.construction.complete.pcr.source import derive_pcr_source
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.molecular_replay import observe_pair
from hop_design.models.molecular_state import (
    CovalentBond,
    LineageStrand,
    MolecularStrand,
    StrandEnd,
)

from .adapter_program import adapter_program
from .associations import annealed_pairings, duplex_pairings, product_pairings
from .lineage import material_strand


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def materialize_adapter_program(
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    prefix: str,
    source_return_arm: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
    adapter: ExactConstructionMaterial,
    material_uses: tuple[MaterialUse, MaterialUse, MaterialUse],
    evaluation: CombinationEvaluation,
    joined_sequence: str,
) -> ConstructionProgram:
    """Materialize the independently validated source-to-adapter-ligated prefix."""
    if evaluation.reaction_program is None or evaluation.rejection_reason is not None:
        raise ValueError("PCR materialization requires one exact compatible direct spine.")
    if evaluation.source_preparation is None or tuple(
        binding.material for binding in evaluation.source_preparation.produced_material_bindings
    ) != (source, source_complement):
        raise ValueError("PCR materialization requires the exact prepared source duplex.")
    reaction = evaluation.reaction_program
    source_use, source_complement_use, adapter_use = material_uses
    initial = evaluation.source_preparation.product_state
    source_result = derive_pcr_source(
        foldback=foldback,
        basal=basal,
        preparation=evaluation.source_preparation,
        partition=evaluation.source_partition_plan,
    )
    if source_result.reaction != reaction:
        raise ValueError("PCR source reaction must equal the evaluated program.")
    product_strands = source_result.cleaved
    cleaved = ConstructionState.create(
        molecules=product_strands,
        phase=ConstructionStatePhase.CLEAVED_DUPLEX,
        pairings=duplex_pairings(
            product_strands,
            source_id=source_use.use_id,
            complement_id=source_complement_use.use_id,
            source_length=len(source.sequence_5prime),
        ),
    )
    selected_fragments = source_result.selected
    denatured_molecules = cleaved.molecules
    denatured = ConstructionState.create(
        molecules=denatured_molecules,
        phase=ConstructionStatePhase.DENATURED_FRAGMENTS,
    )
    selected = ConstructionState.create(
        molecules=selected_fragments,
        phase=ConstructionStatePhase.SELECTED_FRAGMENTS,
    )
    embedding = derive_linear_source_embedding(
        foldback=foldback,
        prefix=prefix,
        source_return_arm=source_return_arm,
    )
    foldback_pairs = annealed_pairings(
        selected.molecules,
        foldback=foldback,
        embedding=embedding,
        source_id=source_use.use_id,
        complement_id=source_complement_use.use_id,
        source_length=len(source.sequence_5prime),
    )
    annealed = ConstructionState.create(
        molecules=selected.molecules,
        phase=ConstructionStatePhase.ANNEALED_COMPLEX,
        pairings=foldback_pairs,
    )
    if not joined_sequence.endswith(adapter.sequence_5prime):
        raise ValueError("PCR template must terminate in the exact ligation adapter.")
    closed_sequence = joined_sequence[: -len(adapter.sequence_5prime)]
    closed_lineage = tuple(
        item.model_copy(update={"product_index": index})
        for index, item in enumerate(
            lineage for strand in selected.molecules for lineage in strand.lineage
        )
    )
    closed = MolecularStrand(
        strand_id="complete-foldback-closed-hairpin",
        sequence=closed_sequence,
        five_prime_end=selected.molecules[0].five_prime_end,
        three_prime_end=selected_fragments[1].three_prime_end,
        lineage=closed_lineage,
    )
    foldback_bond = CovalentBond(
        upstream_strand_id=selected_fragments[0].strand_id,
        upstream_end=StrandEnd.THREE_PRIME,
        downstream_strand_id=selected_fragments[1].strand_id,
        downstream_end=StrandEnd.FIVE_PRIME,
    )
    closed_state = ConstructionState.create(
        molecules=(closed,),
        phase=ConstructionStatePhase.FOLDBACK_CLOSED_HAIRPIN,
        pairings=product_pairings(
            foldback_pairs, precursor_strands=selected.molecules, product=closed
        ),
        formed_bonds=(
            ConstructionBondState(bond=foldback_bond, product_strand_id=closed.strand_id),
        ),
    )
    adapter_strand = material_strand(
        "complete-ligation-adapter",
        adapter,
        lineage_strand=LineageStrand.PRIMARY,
        material_use_id=adapter_use.use_id,
    )
    pairing_state = complete_adapter_pairing(
        basal, source_prefix=prefix, adapter_sequence=adapter.sequence_5prime
    )
    adapter_pairs = tuple(
        observe_pair(
            left_strand_id=closed.strand_id,
            right_strand_id=adapter_strand.strand_id,
            left_index=pair.source_index + pairing_state.source_span.start.offset,
            right_index=pair.adapter_index,
            left_base=pair.source_base,
            right_base=pair.adapter_base,
        )
        for pair in pairing_state.pairs
    )
    adapter_annealed = ConstructionState.create(
        molecules=(closed, adapter_strand),
        phase=ConstructionStatePhase.ADAPTER_ANNEALED,
        pairings=(*closed_state.pairings, *adapter_pairs),
        formed_bonds=closed_state.formed_bonds,
    )
    annealing_authority = AdapterAnnealingAuthority.create(
        pre_state_id=closed_state.state_id,
        post_state_id=adapter_annealed.state_id,
        adapter=adapter,
        adapter_use=adapter_use,
        hairpin_span=pairing_state.source_span,
        adapter_span=pairing_state.adapter_span,
        pairings=adapter_pairs,
    )
    adapter_bond = CovalentBond(
        upstream_strand_id=closed.strand_id,
        upstream_end=StrandEnd.THREE_PRIME,
        downstream_strand_id=adapter_strand.strand_id,
        downstream_end=StrandEnd.FIVE_PRIME,
    )
    ligated = MolecularStrand(
        strand_id="complete-adapter-ligated-hairpin",
        sequence=closed.sequence + adapter.sequence_5prime,
        five_prime_end=closed.five_prime_end,
        three_prime_end=adapter.three_prime_end,
        lineage=tuple(
            item.model_copy(update={"product_index": index})
            for index, item in enumerate((*closed.lineage, *adapter_strand.lineage))
        ),
    )
    ligated_pairs = product_pairings(
        adapter_annealed.pairings,
        precursor_strands=adapter_annealed.molecules,
        product=ligated,
    )
    adapter_ligated = ConstructionState.create(
        molecules=(ligated,),
        phase=ConstructionStatePhase.ADAPTER_LIGATED,
        pairings=ligated_pairs,
        formed_bonds=(
            closed_state.formed_bonds[0].model_copy(
                update={"product_strand_id": ligated.strand_id}
            ),
            ConstructionBondState(bond=adapter_bond, product_strand_id=ligated.strand_id),
        ),
    )
    ligation_authority = AdapterLigationAuthority.create(
        pre_state_id=adapter_annealed.state_id,
        post_state_id=adapter_ligated.state_id,
        adapter=adapter,
        adapter_use=adapter_use,
        bond=adapter_bond,
        product=ligated,
    )
    return adapter_program(
        states=(
            initial,
            cleaved,
            denatured,
            selected,
            annealed,
            closed_state,
            adapter_annealed,
            adapter_ligated,
        ),
        reaction=reaction,
        assessments=evaluation.stage_assessments,
        annealing=annealing_authority,
        ligation=ligation_authority,
    )
