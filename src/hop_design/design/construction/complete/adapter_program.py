"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/adapter_program.py

Assembles the exact typed chronology for one materialized hairpin adapter-ligation route.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.complete import (
    AdapterAnnealingAuthority,
    AdapterLigationAuthority,
    ConstructionProgram,
    ConstructionState,
    ConstructionTransition,
    ConstructionTransitionKind,
    ExactStateRelation,
    ReactionBoundaryMapping,
)
from hop_design.models.reactions import ReactionProgram, ReactionStageAssessment


def _relation(pre: ConstructionState, post: ConstructionState) -> ExactStateRelation:
    return ExactStateRelation.create(pre_state_id=pre.state_id, post_state_id=post.state_id)


def adapter_program(
    *,
    states: tuple[ConstructionState, ...],
    reaction: ReactionProgram,
    assessments: tuple[ReactionStageAssessment, ...],
    annealing: AdapterAnnealingAuthority,
    ligation: AdapterLigationAuthority,
) -> ConstructionProgram:
    """Build the fixed enzyme-to-adapter-ligation transition sequence from exact states."""
    (
        initial,
        cleaved,
        denatured,
        selected,
        foldback_annealed,
        foldback_closed,
        adapter_annealed,
        adapter_ligated,
    ) = states
    boundary = ReactionBoundaryMapping.create(
        reaction_program_id=reaction.program_id,
        pre_state_id=initial.state_id,
        post_state_id=cleaved.state_id,
        pre_strands=initial.molecules,
        post_strands=cleaved.molecules,
        pre_pairings=initial.pairings,
        post_pairings=cleaved.pairings,
        pre_bonds=initial.formed_bonds,
        post_bonds=cleaved.formed_bonds,
    )
    transitions = (
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.ENZYME_PHASE,
            pre_state_id=initial.state_id,
            post_state_id=cleaved.state_id,
            reaction_program_id=reaction.program_id,
            reaction_boundary_mapping=boundary,
        ),
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.DENATURATION,
            pre_state_id=cleaved.state_id,
            post_state_id=denatured.state_id,
            exact_relation=_relation(cleaved, denatured),
        ),
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.FRAGMENT_SELECTION,
            pre_state_id=denatured.state_id,
            post_state_id=selected.state_id,
            exact_relation=_relation(denatured, selected),
        ),
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.ANNEALING,
            pre_state_id=selected.state_id,
            post_state_id=foldback_annealed.state_id,
            exact_relation=_relation(selected, foldback_annealed),
        ),
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.LIGATION,
            pre_state_id=foldback_annealed.state_id,
            post_state_id=foldback_closed.state_id,
            exact_relation=_relation(foldback_annealed, foldback_closed),
        ),
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.ANNEALING,
            pre_state_id=foldback_closed.state_id,
            post_state_id=adapter_annealed.state_id,
            pcr_authority=annealing,
        ),
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.LIGATION,
            pre_state_id=adapter_annealed.state_id,
            post_state_id=adapter_ligated.state_id,
            pcr_authority=ligation,
        ),
    )
    return ConstructionProgram.create(
        states=states,
        transitions=transitions,
        reaction_programs=(reaction,),
        stage_assessments=assessments,
    )


__all__ = ["adapter_program"]
