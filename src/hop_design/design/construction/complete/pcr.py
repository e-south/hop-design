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
    PcrPrimer,
    PrimerExtensionAuthority,
)
from hop_design.models.construction.complete.basal_embedding import basal_nick_boundary
from hop_design.models.construction.complete.evaluation import CombinationEvaluation
from hop_design.models.construction.complete.evaluation_inputs import (
    derive_linear_source_embedding,
)
from hop_design.models.construction.complete.pcr.pairing import complete_adapter_pairing
from hop_design.models.construction.complete.pcr.products import (
    endpoint_fate_spans,
    material_function_spans,
    pcr_products,
)
from hop_design.models.construction.complete.pcr.route import (
    pcr_cleaved_strands,
    select_pcr_fragments,
)
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_replay import observe_pair
from hop_design.models.molecular_state import (
    CovalentBond,
    LineageStrand,
    MolecularStrand,
    PrimerBinding,
    StrandEnd,
)
from hop_design.models.plan import SequenceFeature
from hop_design.models.sequence import reverse_complement_iupac

from .associations import annealed_pairings, duplex_pairings, product_pairings
from .lineage import material_strand
from .materialization import _global_ligation_bond
from .pcr_program import pcr_program


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def materialize_pcr_program(
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    prefix: str,
    source_return_arm: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
    adapter: ExactConstructionMaterial,
    forward_primer: PcrPrimer,
    reverse_primer: PcrPrimer,
    material_uses: tuple[MaterialUse, MaterialUse, MaterialUse, MaterialUse, MaterialUse],
    evaluation: CombinationEvaluation,
    encoding_features: tuple[SequenceFeature, ...],
    design_endpoint_span: Span,
) -> tuple[ConstructionProgram, PrimerExtensionAuthority]:
    """Materialize the exact basal-open intermediate through the PCR duplex."""
    if evaluation.reaction_program is None or evaluation.rejection_reason is not None:
        raise ValueError("PCR materialization requires one exact compatible direct spine.")
    if evaluation.source_preparation is None or tuple(
        binding.material for binding in evaluation.source_preparation.produced_material_bindings
    ) != (source, source_complement):
        raise ValueError("PCR materialization requires the exact prepared source duplex.")
    reaction = evaluation.reaction_program
    source_use, source_complement_use, adapter_use, forward_use, reverse_use = material_uses
    initial = evaluation.source_preparation.product_state
    product_strands = pcr_cleaved_strands(
        reaction,
        foldback=foldback,
        prefix_length=len(prefix),
        source=source,
        source_complement=source_complement,
        source_use_id=source_use.use_id,
        source_complement_use_id=source_complement_use.use_id,
    )
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
    selected_fragments = select_pcr_fragments(
        cleaved.molecules,
        foldback=foldback,
        source_material_use_id=source_use.use_id,
        source_complement_material_use_id=source_complement_use.use_id,
        removed_return_sequence=reverse_complement_iupac(
            prefix[: basal_nick_boundary(basal, prefix)]
        ),
    )
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
    if evaluation.pcr_template_sequence is None:
        raise ValueError("PCR materialization requires one exact PCR template sequence.")
    if not evaluation.pcr_template_sequence.endswith(adapter.sequence_5prime):
        raise ValueError("PCR template must terminate in the exact ligation adapter.")
    closed_sequence = evaluation.pcr_template_sequence[: -len(adapter.sequence_5prime)]
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
    foldback_bond = _global_ligation_bond(foldback, selected.molecules)
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
    top, bottom = pcr_products(
        ligated,
        forward_primer,
        reverse_primer,
        forward_use_id=forward_use.use_id,
        reverse_use_id=reverse_use.use_id,
    )
    duplex_pairs = tuple(
        observe_pair(
            left_strand_id=top.strand_id,
            right_strand_id=bottom.strand_id,
            left_index=index,
            right_index=len(top.sequence) - 1 - index,
            left_base=base,
            right_base=bottom.sequence[len(top.sequence) - 1 - index],
        )
        for index, base in enumerate(top.sequence)
    )
    pcr_state = ConstructionState.create(
        molecules=(top, bottom),
        phase=ConstructionStatePhase.HAIRPIN_PCR_DUPLEX,
        pairings=duplex_pairs,
    )
    bindings = (
        PrimerBinding(
            binding_id="complete-forward-primer-binding",
            primer_id=forward_use.use_id,
            template_strand_id=f"{ligated.strand_id}-derived-complement",
            template_span=_span(0, forward_primer.annealing_length_nt),
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
        PrimerBinding(
            binding_id="complete-reverse-primer-binding",
            primer_id=reverse_use.use_id,
            template_strand_id=ligated.strand_id,
            template_span=_span(
                len(ligated.sequence) - reverse_primer.annealing_length_nt,
                len(ligated.sequence),
            ),
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
    )
    functions = material_function_spans(
        material_uses=material_uses,
        top=top,
        bottom=bottom,
    )
    fates = endpoint_fate_spans(
        encoding_features,
        len(top.sequence),
        design_source_span=design_endpoint_span,
    )
    extension = PrimerExtensionAuthority.create(
        pre_state_id=adapter_ligated.state_id,
        post_state_id=pcr_state.state_id,
        forward_primer=forward_primer,
        reverse_primer=reverse_primer,
        forward_primer_use=forward_use,
        reverse_primer_use=reverse_use,
        material_uses=material_uses,
        bindings=bindings,
        products=(top, bottom),
        pairings=duplex_pairs,
        material_function_spans=functions,
        endpoint_sequence_fate_spans=fates,
    )
    states = (
        initial,
        cleaved,
        denatured,
        selected,
        annealed,
        closed_state,
        adapter_annealed,
        adapter_ligated,
        pcr_state,
    )
    return pcr_program(
        states=states,
        reaction=reaction,
        assessments=evaluation.stage_assessments,
        annealing=annealing_authority,
        ligation=ligation_authority,
        extension=extension,
    ), extension


__all__ = ["materialize_pcr_program"]
