"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/route_schedule.py

Derives the exact enzyme program required by complete direct construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import (
    FoldbackCleavageProgramKind,
    FoldbackLocalRealization,
)
from hop_design.models.construction.payload import SourceOrientation, _content_id
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.physical import SiteOrientation
from hop_design.models.reactions import (
    DeclaredEnzymeBinding,
    ReactionMolecule,
    ReactionOperation,
    ReactionProgram,
    ReactionStage,
    ReactionState,
)

from .evaluation_inputs import derive_linear_source_embedding
from .material import ExactConstructionMaterial
from .route_lineage import lift_reaction_molecules


def _shift_binding(binding: DeclaredEnzymeBinding, offset: int) -> DeclaredEnzymeBinding:
    def shifted(boundary: Boundary | None) -> Boundary | None:
        return None if boundary is None else Boundary(offset=boundary.offset + offset)

    return DeclaredEnzymeBinding(
        recognition_span=Span(
            start=Boundary(offset=binding.recognition_span.start.offset + offset),
            end=Boundary(offset=binding.recognition_span.end.offset + offset),
        ),
        orientation=binding.orientation,
        reference_cut=shifted(binding.reference_cut),
        complement_cut=shifted(binding.complement_cut),
    )


def _reverse_binding(
    binding: DeclaredEnzymeBinding,
    *,
    source_length: int,
) -> DeclaredEnzymeBinding:
    """Map one local binding onto the opposite physical strand orientation."""

    def reversed_boundary(boundary: Boundary | None) -> Boundary | None:
        return None if boundary is None else Boundary(offset=source_length - boundary.offset)

    return DeclaredEnzymeBinding(
        recognition_span=Span(
            start=Boundary(offset=source_length - binding.recognition_span.end.offset),
            end=Boundary(offset=source_length - binding.recognition_span.start.offset),
        ),
        orientation=(
            SiteOrientation.REVERSE
            if binding.orientation is SiteOrientation.FORWARD
            else SiteOrientation.FORWARD
        ),
        reference_cut=reversed_boundary(binding.complement_cut),
        complement_cut=reversed_boundary(binding.reference_cut),
    )


def _operation(
    operation: ReactionOperation,
    *,
    namespace: str,
    binding_offset: int = 0,
    reverse_source_length: int | None = None,
) -> ReactionOperation:
    binding = operation.intended_binding
    if reverse_source_length is not None:
        binding = _reverse_binding(binding, source_length=reverse_source_length)
    if binding_offset:
        binding = _shift_binding(binding, binding_offset)
    return ReactionOperation(
        operation_id=f"{namespace}-{operation.operation_id}",
        enzyme_id=operation.enzyme_id,
        role=operation.role,
        molecule_id=f"{namespace}-source",
        intended_binding=binding,
    )


def _state(
    *,
    namespace: str,
    index: int,
    molecules: tuple[ReactionMolecule, ...],
) -> ReactionState:
    return ReactionState(
        state_id=f"{namespace}-state-{index}",
        molecules=tuple(
            molecule.model_copy(update={"molecule_id": f"{namespace}-{molecule.molecule_id}"})
            for molecule in molecules
        ),
    )


def derive_direct_reaction_program(
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord | None,
    prefix: str,
    source_return_arm: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> ReactionProgram:
    """Derive exact operations and states from the two detailed local authorities."""
    local = foldback.reaction_program
    embedding = derive_linear_source_embedding(
        foldback=foldback,
        prefix=prefix,
        source_return_arm=source_return_arm,
    )
    if (
        source.sequence_5prime != embedding.source_sequence
        or source_complement.sequence_5prime != embedding.complement_sequence
    ):
        raise ValueError("Complete route materials must equal the exact source embedding.")
    lifted = tuple(
        lift_reaction_molecules(
            state.molecules,
            foldback=foldback,
            embedding=embedding,
            source=source,
            source_complement=source_complement,
        )
        for state in local.states
    )
    namespace = (
        _content_id(
            "route-schedule",
            1,
            {
                "foldback": foldback.foldback_realization_id,
                "basal": None if basal is None else basal.basal_realization_id,
            },
        )
        .split("/")[-1]
        .split("@")[0][:12]
    )
    basal_operations: tuple[ReactionOperation, ...] = ()
    if basal is not None:
        if len(basal.reaction_programs) != 1 or len(basal.reaction_programs[0].stages) != 1:
            raise ValueError("Pre-hairpin composition requires one exact basal nick phase.")
        basal_operations = tuple(
            _operation(
                operation,
                namespace=namespace,
                reverse_source_length=(
                    len(source.sequence_5prime)
                    if embedding.source_orientation is SourceOrientation.REVERSE_COMPLEMENT
                    else None
                ),
            )
            for operation in basal.reaction_programs[0].stages[0].operations
        )
    if foldback.program_kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE:
        states: tuple[ReactionState, ...] = (
            _state(namespace=namespace, index=0, molecules=lifted[0]),
            _state(namespace=namespace, index=1, molecules=lifted[-1]),
        )
        stages: tuple[ReactionStage, ...] = (
            ReactionStage(
                stage_id=f"{namespace}-concurrent-nicks",
                pre_state_id=states[0].state_id,
                post_state_id=states[1].state_id,
                operations=basal_operations
                + tuple(
                    _operation(
                        operation,
                        namespace=namespace,
                        binding_offset=embedding.local_reference_offset,
                    )
                    for operation in local.stages[0].operations
                ),
            ),
        )
    else:
        states = tuple(
            _state(namespace=namespace, index=index, molecules=molecules)
            for index, molecules in enumerate(lifted)
        )
        stages = (
            ReactionStage(
                stage_id=f"{namespace}-terminus-definition",
                pre_state_id=states[0].state_id,
                post_state_id=states[1].state_id,
                operations=tuple(
                    _operation(
                        operation,
                        namespace=namespace,
                        binding_offset=embedding.local_reference_offset,
                    )
                    for operation in local.stages[0].operations
                ),
            ),
            ReactionStage(
                stage_id=f"{namespace}-concurrent-nicks",
                pre_state_id=states[1].state_id,
                post_state_id=states[2].state_id,
                operations=basal_operations
                + tuple(
                    _operation(
                        operation,
                        namespace=namespace,
                        binding_offset=embedding.local_reference_offset,
                    )
                    for operation in local.stages[1].operations
                ),
            ),
        )
    return ReactionProgram(
        program_id=f"complete-route-{namespace}",
        states=states,
        stages=stages,
    )


__all__ = ["derive_direct_reaction_program"]
