"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/replay.py

Replays selected source-partition evidence against exact complete-route facts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import NoReturn

from hop_design.models.construction.complete.material import (
    ExactConstructionMaterial,
    MaterialUse,
)
from hop_design.models.construction.complete.program import ConstructionProgram
from hop_design.models.construction.complete.source_preparation import (
    SourceDuplexPreparationAuthority,
)
from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.complete.transition import ConstructionTransitionKind
from hop_design.models.construction.payload import FinalPayloadReference, PayloadSourceMap
from hop_design.models.construction.source_partition.result import (
    SourcePartitionDiscoveryResult,
    SourcePartitionRealization,
)
from hop_design.models.enzymes import CharacterizedEnzyme
from hop_design.models.reactions import ReactionProgram

from .binding import SourcePartitionBinding
from .errors import SourcePartitionBindingError, SourcePartitionBindingFailure
from .facts import route_cut_facts, validate_source_facts
from .reaction import derive_partition_reaction_program
from .selection import validate_partition_selection


def _fail(code: SourcePartitionBindingFailure, message: str) -> NoReturn:
    raise SourcePartitionBindingError(code, message)


def _selected_realization(
    result: SourcePartitionDiscoveryResult,
    realization_id: str,
) -> SourcePartitionRealization:
    verified = SourcePartitionDiscoveryResult.model_validate(result.model_dump(mode="python"))
    for realization in verified.realizations:
        if realization.realization_id == realization_id:
            return realization
    _fail(
        SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
        "The selected realization is not present in the partition result.",
    )


def _route_partition_program(
    construction_program: ConstructionProgram,
) -> tuple[ReactionProgram, ConstructionState, ConstructionState]:
    if not construction_program.reaction_programs:
        _fail(
            SourcePartitionBindingFailure.STAGE_INCOMPATIBLE,
            "A selected partition requires one pre-hairpin reaction program.",
        )
    program = construction_program.reaction_programs[0]
    enzyme_transitions = tuple(
        item
        for item in construction_program.transitions
        if item.reaction_program_id == program.program_id
    )
    if (
        len(enzyme_transitions) != 1
        or enzyme_transitions[0].kind is not ConstructionTransitionKind.ENZYME_PHASE
    ):
        _fail(
            SourcePartitionBindingFailure.STAGE_INCOMPATIBLE,
            "The first reaction program must bind one pre-hairpin enzyme phase.",
        )
    transition = enzyme_transitions[0]
    if len(program.stages) != 1:
        _fail(
            SourcePartitionBindingFailure.STAGE_INCOMPATIBLE,
            "The pre-hairpin route must contain exactly one concurrent reaction stage.",
        )
    stage = program.stages[0]
    if any(
        (operation.intended_binding.reference_cut is None)
        == (operation.intended_binding.complement_cut is None)
        for operation in stage.operations
    ):
        _fail(
            SourcePartitionBindingFailure.STAGE_INCOMPATIBLE,
            "Every source-partition operation must be one strand-specific nick.",
        )
    states = {item.state_id: item for item in construction_program.states}
    denaturation = next(
        (
            item
            for item in construction_program.transitions
            if item.kind is ConstructionTransitionKind.DENATURATION
            and item.pre_state_id == transition.post_state_id
        ),
        None,
    )
    selection = next(
        (
            item
            for item in construction_program.transitions
            if item.kind is ConstructionTransitionKind.FRAGMENT_SELECTION
            and denaturation is not None
            and item.pre_state_id == denaturation.post_state_id
        ),
        None,
    )
    if denaturation is None or selection is None:
        _fail(
            SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
            "The pre-hairpin stage must lead through denaturation and fragment selection.",
        )
    return program, states[denaturation.post_state_id], states[selection.post_state_id]


def bind_source_partition(
    *,
    payload: FinalPayloadReference,
    payload_source_map: PayloadSourceMap,
    source_preparation: SourceDuplexPreparationAuthority,
    construction_program: ConstructionProgram,
    materials: tuple[ExactConstructionMaterial, ...],
    material_uses: tuple[MaterialUse, ...],
    route_enzyme_definitions: tuple[CharacterizedEnzyme, ...],
    partition_result: SourcePartitionDiscoveryResult,
    selected_realization_id: str,
) -> SourcePartitionBinding:
    """Bind one selected partition to exact route states without sharing representation ids."""
    realization = _selected_realization(partition_result, selected_realization_id)
    top_use, bottom_use = validate_source_facts(
        payload=payload,
        payload_source_map=payload_source_map,
        source_preparation=source_preparation,
        construction_program=construction_program,
        materials=materials,
        material_uses=material_uses,
        partition_result=partition_result,
    )
    program, denatured_state, selected_state = _route_partition_program(construction_program)
    expected_program = derive_partition_reaction_program(realization)
    if route_cut_facts(program, route_enzyme_definitions) != route_cut_facts(
        expected_program,
        partition_result.request.enzyme_provisioning.catalog.enzymes,
    ):
        _fail(
            SourcePartitionBindingFailure.CUT_INCOMPATIBLE,
            "Route nick facts must equal the selected partition nick multiset.",
        )
    validate_partition_selection(
        realization=realization,
        partition_result=partition_result,
        denatured_state=denatured_state,
        selected_state=selected_state,
        source_length=len(partition_result.request.source.top_sequence_5prime),
        top_use_id=top_use.use_id,
        bottom_use_id=bottom_use.use_id,
    )
    return SourcePartitionBinding.create(
        result_id=partition_result.result_id,
        realization_id=realization.realization_id,
        source_preparation_product_state_id=source_preparation.product_state.state_id,
        top_material_use_id=top_use.use_id,
        bottom_material_use_id=bottom_use.use_id,
        reaction_program_id=program.program_id,
        denatured_state_id=denatured_state.state_id,
        selected_state_id=selected_state.state_id,
    )


__all__ = ["bind_source_partition"]
