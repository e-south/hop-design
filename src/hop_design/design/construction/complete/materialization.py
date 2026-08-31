"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/materialization.py

Materializes exact complete-route states from local foldback and basal authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.complete import (
    ConstructionBondState,
    ConstructionProgram,
    ConstructionState,
    ConstructionStatePhase,
    ConstructionTransition,
    ConstructionTransitionKind,
    ExactConstructionMaterial,
    ExactStateRelation,
    ReactionBoundaryMapping,
)
from hop_design.models.construction.complete.evaluation import CombinationEvaluation
from hop_design.models.construction.complete.evaluation_inputs import (
    derive_linear_source_embedding,
)
from hop_design.models.construction.complete.route_lineage import (
    derive_post_cleavage_strands,
    material_strand,
)
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import CovalentBond, LineageStrand, MolecularStrand
from hop_design.models.reactions import (
    ReactionProgram,
)

from .associations import annealed_pairings, duplex_pairings, product_pairings
from .lineage import (
    final_hairpin_strand,
)


def _reaction_boundary_mapping(
    *,
    program: ReactionProgram,
    pre_state: ConstructionState,
    post_state: ConstructionState,
) -> ReactionBoundaryMapping:
    return ReactionBoundaryMapping.create(
        reaction_program_id=program.program_id,
        pre_state_id=pre_state.state_id,
        post_state_id=post_state.state_id,
        pre_strands=pre_state.molecules,
        post_strands=post_state.molecules,
        pre_pairings=pre_state.pairings,
        post_pairings=post_state.pairings,
        pre_bonds=pre_state.formed_bonds,
        post_bonds=post_state.formed_bonds,
    )


def _global_ligation_bond(
    foldback: FoldbackLocalRealization,
    strands: tuple[MolecularStrand, ...],
) -> CovalentBond:
    local = foldback.ligation_bond

    def resolve(local_id: str) -> str:
        matches = tuple(item.strand_id for item in strands if f"-{local_id}-" in item.strand_id)
        if len(matches) != 1:
            raise ValueError("Ligation bond must map to one exact selected route strand.")
        return matches[0]

    return local.model_copy(
        update={
            "upstream_strand_id": resolve(local.upstream_strand_id),
            "downstream_strand_id": resolve(local.downstream_strand_id),
        }
    )


def materialize_direct_program(
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord | None,
    prefix: str,
    source_return_arm: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
    evaluation: CombinationEvaluation,
) -> tuple[ConstructionProgram, MolecularStrand] | None:
    """Materialize one exact source-to-ssDNA-hairpin chronology."""
    if (
        evaluation.rejection_reason is not None
        or evaluation.reaction_program is None
        or evaluation.source != source
        or evaluation.source_complement != source_complement
        or evaluation.prefix != prefix
        or evaluation.source_return_arm != source_return_arm
    ):
        return None
    reaction = evaluation.reaction_program
    assessments = evaluation.stage_assessments
    released_molecules = reaction.states[-1].molecules
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
    states = [initial]
    transitions = []
    embedding = derive_linear_source_embedding(
        foldback=foldback,
        prefix=prefix,
        source_return_arm=source_return_arm,
    )
    exact_product_strands = derive_post_cleavage_strands(
        released_molecules,
        namespace="foldback-enzyme-product",
        foldback=foldback,
        embedding=embedding,
        source=source,
        source_complement=source_complement,
    )
    enzyme_product = ConstructionState.create(
        molecules=exact_product_strands,
        phase=ConstructionStatePhase.CLEAVED_DUPLEX,
        pairings=duplex_pairings(
            exact_product_strands,
            source_id=source.material_id,
            complement_id=source_complement.material_id,
            source_length=len(source.sequence_5prime),
        ),
    )
    released_strands = derive_post_cleavage_strands(
        released_molecules,
        namespace="foldback-released",
        foldback=foldback,
        embedding=embedding,
        source=source,
        source_complement=source_complement,
    )
    released = ConstructionState.create(
        molecules=released_strands,
        phase=ConstructionStatePhase.DENATURED_FRAGMENTS,
    )
    if any(molecule.complement_sequence_5prime is not None for molecule in released_molecules):
        raise ValueError("Foldback post-state selection requires exact single-strand fragments.")
    selected = ConstructionState.create(
        molecules=tuple(
            strand
            for molecule, strand in zip(released_molecules, released.molecules, strict=True)
            if not any(
                molecule.molecule_id.endswith(fragment_id)
                for fragment_id in foldback.released_fragment_ids
            )
        ),
        phase=ConstructionStatePhase.SELECTED_FRAGMENTS,
    )
    # Family replay establishes the exact ligation substrate; composition extends it
    # with the retained source prefix and its antiparallel source return arm.
    ligation_bond = _global_ligation_bond(foldback, selected.molecules)
    final = final_hairpin_strand(
        foldback=foldback,
        prefix=prefix,
        source_return_arm=source_return_arm,
        selected_strands=selected.molecules,
        ligation_bond=ligation_bond,
    )
    annealed_pairs = annealed_pairings(
        selected.molecules,
        foldback=foldback,
        embedding=embedding,
        source_id=source.material_id,
        complement_id=source_complement.material_id,
        source_length=len(source.sequence_5prime),
    )
    annealed = ConstructionState.create(
        molecules=selected.molecules,
        phase=ConstructionStatePhase.ANNEALED_COMPLEX,
        pairings=annealed_pairs,
    )
    ligated = ConstructionState.create(
        molecules=(final,),
        phase=ConstructionStatePhase.LIGATED_PRODUCT,
        pairings=product_pairings(
            annealed_pairs,
            precursor_strands=selected.molecules,
            product=final,
        ),
        formed_bonds=(
            ConstructionBondState(
                bond=ligation_bond,
                product_strand_id=final.strand_id,
            ),
        ),
    )
    states.extend((enzyme_product, released, selected, annealed, ligated))
    transitions.append(
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.ENZYME_PHASE,
            pre_state_id=initial.state_id,
            post_state_id=enzyme_product.state_id,
            reaction_program_id=reaction.program_id,
            reaction_boundary_mapping=_reaction_boundary_mapping(
                program=reaction,
                pre_state=initial,
                post_state=enzyme_product,
            ),
        )
    )
    denaturation = ExactStateRelation.create(
        pre_state_id=enzyme_product.state_id,
        post_state_id=released.state_id,
    )
    transitions.append(
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.DENATURATION,
            pre_state_id=enzyme_product.state_id,
            post_state_id=released.state_id,
            exact_relation=denaturation,
        )
    )
    kinds = (
        ConstructionTransitionKind.FRAGMENT_SELECTION,
        ConstructionTransitionKind.ANNEALING,
        ConstructionTransitionKind.LIGATION,
    )
    for index, kind in enumerate(kinds):
        pre_state = (released, selected, annealed)[index]
        post_state = (selected, annealed, ligated)[index]
        relation = ExactStateRelation.create(
            pre_state_id=pre_state.state_id,
            post_state_id=post_state.state_id,
        )
        transitions.append(
            ConstructionTransition.create(
                kind=kind,
                pre_state_id=pre_state.state_id,
                post_state_id=post_state.state_id,
                exact_relation=relation,
            )
        )
    return (
        ConstructionProgram.create(
            states=tuple(states),
            transitions=tuple(transitions),
            reaction_programs=(reaction,),
            stage_assessments=assessments,
        ),
        final,
    )


__all__ = ["materialize_direct_program"]
