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
from hop_design.models.construction.payload import ConstructionEndpoint, _content_id
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.reactions import (
    DeclaredEnzymeBinding,
    ReactionMolecule,
    ReactionOperation,
    ReactionProgram,
    ReactionStage,
    ReactionState,
)
from hop_design.models.sequence import reverse_complement_iupac


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


def _lift_molecule(
    molecule: ReactionMolecule,
    *,
    payload: str,
    prefix: str,
    return_arm: str,
) -> ReactionMolecule:
    reference = molecule.reference_sequence_5prime
    complement = molecule.complement_sequence_5prime
    if reference.startswith(payload):
        reference = prefix + reference
        if complement is not None:
            complement += return_arm
    elif complement is None and reference.endswith(reverse_complement_iupac(payload)):
        reference += return_arm
    return ReactionMolecule(
        molecule_id=molecule.molecule_id,
        reference_sequence_5prime=reference,
        complement_sequence_5prime=complement,
    )


def _operation(
    operation: ReactionOperation,
    *,
    namespace: str,
    binding_offset: int = 0,
) -> ReactionOperation:
    binding = operation.intended_binding
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
    return_arm: str,
) -> ReactionProgram:
    """Derive exact operations and states from the two detailed local authorities."""
    local = foldback.reaction_program
    lifted = tuple(
        tuple(
            _lift_molecule(
                molecule,
                payload=foldback.payload_sequence,
                prefix=prefix,
                return_arm=return_arm,
            )
            for molecule in state.molecules
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
        expected_program_count = (
            2 if basal.projection.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX else 1
        )
        if (
            len(basal.reaction_programs) != expected_program_count
            or len(basal.reaction_programs[0].stages) != 1
        ):
            raise ValueError("Pre-hairpin composition requires one exact basal nick phase.")
        basal_operations = tuple(
            _operation(operation, namespace=namespace)
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
                    _operation(operation, namespace=namespace, binding_offset=len(prefix))
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
                    _operation(operation, namespace=namespace, binding_offset=len(prefix))
                    for operation in local.stages[0].operations
                ),
            ),
            ReactionStage(
                stage_id=f"{namespace}-concurrent-nicks",
                pre_state_id=states[1].state_id,
                post_state_id=states[2].state_id,
                operations=basal_operations
                + tuple(
                    _operation(operation, namespace=namespace, binding_offset=len(prefix))
                    for operation in local.stages[1].operations
                ),
            ),
        )
    return ReactionProgram(
        program_id=f"complete-route-{namespace}",
        states=states,
        stages=stages,
    )


def derive_pcr_reaction_program(
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    prefix: str,
    return_arm: str,
) -> ReactionProgram:
    """Derive the exact basal-nicked program with a split complement product."""
    direct = derive_direct_reaction_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        return_arm=return_arm,
    )
    final = direct.states[-1]
    molecules: list[ReactionMolecule] = []
    split_count = 0
    for molecule in final.molecules:
        if (
            molecule.complement_sequence_5prime is None
            and "bottom-" in molecule.molecule_id
            and molecule.reference_sequence_5prime.endswith(return_arm)
            and len(molecule.reference_sequence_5prime) > len(return_arm)
        ):
            split_count += 1
            sequence = molecule.reference_sequence_5prime
            split = len(sequence) - len(return_arm)
            molecules.extend(
                (
                    ReactionMolecule(
                        molecule_id=f"{molecule.molecule_id}-pcr-bottom-retained",
                        reference_sequence_5prime=sequence[:split],
                        complement_sequence_5prime=None,
                    ),
                    ReactionMolecule(
                        molecule_id=f"{molecule.molecule_id}-pcr-bottom-return-arm",
                        reference_sequence_5prime=sequence[split:],
                        complement_sequence_5prime=None,
                    ),
                )
            )
            continue
        if molecule.complement_sequence_5prime is None:
            molecules.append(molecule)
            continue
        split_count += 1
        complement = molecule.complement_sequence_5prime
        split = len(complement) - len(return_arm)
        molecules.extend(
            (
                ReactionMolecule(
                    molecule_id=f"{molecule.molecule_id}-top",
                    reference_sequence_5prime=molecule.reference_sequence_5prime,
                    complement_sequence_5prime=None,
                ),
                ReactionMolecule(
                    molecule_id=f"{molecule.molecule_id}-pcr-bottom-retained",
                    reference_sequence_5prime=complement[:split],
                    complement_sequence_5prime=None,
                ),
                ReactionMolecule(
                    molecule_id=f"{molecule.molecule_id}-pcr-bottom-return-arm",
                    reference_sequence_5prime=complement[split:],
                    complement_sequence_5prime=None,
                ),
            )
        )
    if split_count != 1:
        raise ValueError("PCR reaction program must split one exact complement strand.")
    states = (*direct.states[:-1], final.model_copy(update={"molecules": tuple(molecules)}))
    stages = tuple(
        stage.model_copy(update={"post_state_id": states[index + 1].state_id})
        for index, stage in enumerate(direct.stages)
    )
    program_digest = (
        _content_id(
            "pcr-reaction-program",
            1,
            {
                "foldback_realization_id": foldback.foldback_realization_id,
                "basal_realization_id": basal.basal_realization_id,
                "prefix": prefix,
                "return_arm": return_arm,
                "states": tuple(item.model_dump(mode="json") for item in states),
                "stages": tuple(item.model_dump(mode="json") for item in stages),
            },
        )
        .split("/")[-1]
        .split("@")[0]
    )
    return ReactionProgram(program_id=f"pcr-route-{program_digest}", states=states, stages=stages)


__all__ = ["derive_direct_reaction_program", "derive_pcr_reaction_program"]
