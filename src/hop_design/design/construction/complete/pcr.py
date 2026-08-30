"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/pcr.py

Materializes one exact basal-open hairpin PCR construction endpoint.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.molecular_replay import observe_pair
from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.complete import (
    AdapterAnnealingAuthority,
    AdapterLigationAuthority,
    ConstructionBondState,
    ConstructionProgram,
    ConstructionState,
    ConstructionStatePhase,
    ExactConstructionMaterial,
    PrimerExtensionAuthority,
)
from hop_design.models.construction.complete.evaluation import CombinationEvaluation
from hop_design.models.construction.complete.pcr.products import (
    endpoint_fate_spans,
    material_function_spans,
    pcr_products,
)
from hop_design.models.construction.complete.pcr.route import (
    pcr_cleaved_strands,
    select_pcr_fragments,
)
from hop_design.models.construction.complete.route_lineage import material_strand
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import (
    CovalentBond,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
    PrimerBinding,
    StrandEnd,
)
from hop_design.models.plan import SequenceFeature

from .associations import annealed_pairings, duplex_pairings, product_pairings
from .materialization import _global_ligation_bond
from .pcr_program import pcr_program


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _lineage_strand(material: ExactConstructionMaterial) -> MolecularStrand:
    return MolecularStrand(
        strand_id="complete-ligation-adapter",
        sequence=material.sequence_5prime,
        five_prime_end=material.five_prime_end,
        three_prime_end=material.three_prime_end,
        lineage=tuple(
            MaterialBaseLineage(
                product_index=index,
                origin_id=material.material_id,
                origin_strand=LineageStrand.PRIMARY,
                origin_index=index,
            )
            for index in range(len(material.sequence_5prime))
        ),
    )


def materialize_pcr_program(
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    prefix: str,
    return_arm: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
    adapter: ExactConstructionMaterial,
    forward_primer: ExactConstructionMaterial,
    reverse_primer: ExactConstructionMaterial,
    evaluation: CombinationEvaluation,
    encoding_features: tuple[SequenceFeature, ...],
    design_source_span: Span,
) -> tuple[ConstructionProgram, PrimerExtensionAuthority]:
    """Materialize the exact basal-open intermediate through the PCR duplex."""
    if evaluation.reaction_program is None or evaluation.rejection_reason is not None:
        raise ValueError("PCR materialization requires one exact compatible direct spine.")
    reaction = evaluation.reaction_program
    initial_molecules = (
        material_strand("source-top", source, lineage_strand=LineageStrand.PRIMARY),
        material_strand(
            "source-bottom",
            source_complement,
            lineage_strand=LineageStrand.COMPLEMENTARY,
        ),
    )
    initial = ConstructionState.create(
        molecules=initial_molecules,
        phase=ConstructionStatePhase.DUPLEX,
        pairings=duplex_pairings(
            initial_molecules,
            source_id=source.material_id,
            complement_id=source_complement.material_id,
            source_length=len(source.sequence_5prime),
        ),
    )
    product_strands = pcr_cleaved_strands(
        reaction,
        foldback=foldback,
        prefix_length=len(prefix),
        source=source,
        source_complement=source_complement,
    )
    cleaved = ConstructionState.create(
        molecules=product_strands,
        phase=ConstructionStatePhase.CLEAVED_DUPLEX,
        pairings=duplex_pairings(
            product_strands,
            source_id=source.material_id,
            complement_id=source_complement.material_id,
            source_length=len(source.sequence_5prime),
        ),
    )
    selected_fragments = select_pcr_fragments(
        cleaved.molecules,
        foldback=foldback,
        source_material_id=source.material_id,
        source_complement_material_id=source_complement.material_id,
        return_arm=return_arm,
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
    foldback_pairs = annealed_pairings(
        selected.molecules,
        foldback=foldback,
        source_id=source.material_id,
        complement_id=source_complement.material_id,
        source_length=len(source.sequence_5prime),
    )
    annealed = ConstructionState.create(
        molecules=selected.molecules,
        phase=ConstructionStatePhase.ANNEALED_COMPLEX,
        pairings=foldback_pairs,
    )
    if evaluation.pcr_template_sequence is None:
        raise ValueError("PCR materialization requires one exact PCR template sequence.")
    closed_sequence = evaluation.pcr_template_sequence.removesuffix(return_arm)
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
    adapter_strand = _lineage_strand(adapter)
    profile = basal.projection.pairing_profile
    if profile is None or adapter.sequence_5prime != return_arm:
        raise ValueError("PCR adapter must equal the exact omitted basal return arm.")
    adapter_pairs = tuple(
        observe_pair(
            left_strand_id=closed.strand_id,
            right_strand_id=adapter_strand.strand_id,
            left_index=pair.source_index + profile.source_span.start.offset,
            right_index=pair.adapter_index,
            left_base=pair.source_base,
            right_base=pair.adapter_base,
        )
        for pair in profile.pairs
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
        hairpin_span=profile.source_span,
        adapter_span=profile.adapter_span,
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
        bond=adapter_bond,
        product=ligated,
    )
    top, bottom = pcr_products(ligated, forward_primer, reverse_primer)
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
            primer_id=forward_primer.material_id,
            template_strand_id=f"{ligated.strand_id}-derived-complement",
            template_span=_span(
                len(ligated.sequence) - len(forward_primer.sequence_5prime), len(ligated.sequence)
            ),
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
        PrimerBinding(
            binding_id="complete-reverse-primer-binding",
            primer_id=reverse_primer.material_id,
            template_strand_id=ligated.strand_id,
            template_span=_span(
                len(ligated.sequence) - len(reverse_primer.sequence_5prime), len(ligated.sequence)
            ),
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
    )
    functions = material_function_spans(
        materials=(source, source_complement, adapter, forward_primer, reverse_primer),
        top=top,
        bottom=bottom,
    )
    fates = endpoint_fate_spans(
        encoding_features,
        len(ligated.sequence),
        design_source_span=design_source_span,
    )
    extension = PrimerExtensionAuthority.create(
        pre_state_id=adapter_ligated.state_id,
        post_state_id=pcr_state.state_id,
        forward_primer=forward_primer,
        reverse_primer=reverse_primer,
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
