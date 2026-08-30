"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pcr/schedule.py

Derives the exact reaction schedule required by hairpin PCR construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.construction.payload import SourceOrientation, _content_id
from hop_design.models.reactions import ReactionMolecule, ReactionProgram

from ..evaluation_inputs import derive_linear_source_embedding
from ..request import ExactConstructionMaterial
from ..route_schedule import derive_direct_reaction_program


def derive_pcr_reaction_program(
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    prefix: str,
    return_arm: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> ReactionProgram:
    """Derive the exact basal-nicked program with a split return-arm product."""
    direct = derive_direct_reaction_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        return_arm=return_arm,
        source=source,
        source_complement=source_complement,
    )
    embedding = derive_linear_source_embedding(
        foldback=foldback,
        prefix=prefix,
        return_arm=return_arm,
    )
    final = direct.states[-1]
    molecules: list[ReactionMolecule] = []
    split_count = 0
    for molecule in final.molecules:
        if (
            embedding.source_orientation is SourceOrientation.FORWARD
            and molecule.complement_sequence_5prime is None
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
        if (
            embedding.source_orientation is SourceOrientation.REVERSE_COMPLEMENT
            and molecule.complement_sequence_5prime is None
            and "top-" in molecule.molecule_id
            and molecule.reference_sequence_5prime.endswith(return_arm)
            and len(molecule.reference_sequence_5prime) > len(return_arm)
        ):
            split_count += 1
            sequence = molecule.reference_sequence_5prime
            split = len(sequence) - len(return_arm)
            molecules.extend(
                (
                    ReactionMolecule(
                        molecule_id=f"{molecule.molecule_id}-pcr-top-retained",
                        reference_sequence_5prime=sequence[:split],
                        complement_sequence_5prime=None,
                    ),
                    ReactionMolecule(
                        molecule_id=f"{molecule.molecule_id}-pcr-top-return-arm",
                        reference_sequence_5prime=sequence[split:],
                        complement_sequence_5prime=None,
                    ),
                )
            )
            continue
        if molecule.complement_sequence_5prime is None:
            molecules.append(molecule)
            continue
        if embedding.source_orientation is not SourceOrientation.FORWARD:
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
        raise ValueError("PCR reaction program must split one exact return-arm strand.")
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


__all__ = ["derive_pcr_reaction_program"]
