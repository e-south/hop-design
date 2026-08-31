"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/replay.py

Replays local foldback and source-material facts across complete routes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import LineageStrand
from hop_design.models.sequence import reverse_complement_iupac

from ..evaluation_inputs import replay_linear_source_embedding
from ..pairing_replay import annealed_pairings, duplex_pairings
from ..program import ConstructionProgram
from ..route_lineage import derive_post_cleavage_strands
from ..route_schedule import derive_direct_reaction_program
from ..state import ConstructionStatePhase
from .spec import ExactConstructionMaterial
from .use import MaterialUse


def validate_route_material_lineage(
    program: ConstructionProgram,
    materials: tuple[ExactConstructionMaterial, ...],
    *,
    material_uses: tuple[MaterialUse, ...],
    material_orientations: dict[str, LineageStrand],
) -> None:
    """Require every state base to retain one exact declared material origin."""
    material_by_id = {
        material_use.use_id: material
        for material, material_use in zip(materials, material_uses, strict=True)
    }
    for state in program.states:
        for strand in state.molecules:
            for index, lineage in enumerate(strand.lineage):
                material = material_by_id.get(lineage.origin_id)
                expected_base = (
                    None
                    if material is None or lineage.origin_index >= len(material.sequence_5prime)
                    else material.sequence_5prime[lineage.origin_index]
                )
                baseline_orientation = material_orientations.get(lineage.origin_id)
                if (
                    expected_base is not None
                    and baseline_orientation is not None
                    and lineage.origin_strand is not baseline_orientation
                ):
                    expected_base = reverse_complement_iupac(expected_base)
                if (
                    material is None
                    or baseline_orientation is None
                    or lineage.origin_index >= len(material.sequence_5prime)
                    or strand.sequence[index] != expected_base
                ):
                    raise ValueError(
                        "Construction-state lineage must replay exact declared material bytes: "
                        f"phase={state.phase.value}, strand={strand.strand_id}, "
                        f"base={index}, origin={lineage.origin_id}."
                    )


def validate_foldback_annealing(
    program: ConstructionProgram,
    *,
    foldback: FoldbackLocalRealization,
    materials: tuple[ExactConstructionMaterial, ...],
    material_uses: tuple[MaterialUse, ...],
) -> None:
    """Bind the complete annealed complex to exact local foldback evidence."""
    selected = next(
        item for item in program.states if item.phase is ConstructionStatePhase.SELECTED_FRAGMENTS
    )
    annealed = next(
        item for item in program.states if item.phase is ConstructionStatePhase.ANNEALED_COMPLEX
    )
    _, _, embedding = replay_linear_source_embedding(
        foldback=foldback,
        source_sequence=materials[0].sequence_5prime,
        complement_sequence=materials[1].sequence_5prime,
    )
    expected = annealed_pairings(
        selected.molecules,
        foldback=foldback,
        embedding=embedding,
        source_id=material_uses[0].use_id,
        complement_id=material_uses[1].use_id,
        source_length=len(materials[0].sequence_5prime),
    )
    if annealed.pairings != expected:
        raise ValueError("Complete route annealing associations must equal foldback authority.")


def validate_route_derivation(
    program: ConstructionProgram,
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord | None,
    materials: tuple[ExactConstructionMaterial, ...],
    material_uses: tuple[MaterialUse, ...],
) -> None:
    """Replay the global enzyme program and fragments from exact local authorities."""
    source, source_complement = materials[:2]
    prefix, source_return_arm, embedding = replay_linear_source_embedding(
        foldback=foldback,
        source_sequence=source.sequence_5prime,
        complement_sequence=source_complement.sequence_5prime,
    )
    expected_program = derive_direct_reaction_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        source_return_arm=source_return_arm,
        source=source,
        source_complement=source_complement,
    )
    if program.reaction_programs != (expected_program,):
        raise ValueError("Complete enzyme operations must derive from exact local authorities.")
    molecules = expected_program.states[-1].molecules
    expected_product = derive_post_cleavage_strands(
        molecules,
        namespace="foldback-enzyme-product",
        foldback=foldback,
        embedding=embedding,
        source=source,
        source_complement=source_complement,
        source_use_id=material_uses[0].use_id,
        source_complement_use_id=material_uses[1].use_id,
    )
    expected_released = derive_post_cleavage_strands(
        molecules,
        namespace="foldback-released",
        foldback=foldback,
        embedding=embedding,
        source=source,
        source_complement=source_complement,
        source_use_id=material_uses[0].use_id,
        source_complement_use_id=material_uses[1].use_id,
    )
    if program.states[1].molecules != expected_product or (
        program.states[2].molecules != expected_released
    ):
        raise ValueError(
            "Post-cleavage strands must replay exact fragment chemistry and lineage coordinates."
        )
    expected_cleaved_pairings = duplex_pairings(
        expected_product,
        source_id=material_uses[0].use_id,
        complement_id=material_uses[1].use_id,
        source_length=len(source.sequence_5prime),
    )
    if program.states[1].pairings != expected_cleaved_pairings:
        raise ValueError("Cleaved duplex pairings must replay exact retained material coordinates.")


__all__ = [
    "validate_foldback_annealing",
    "validate_route_derivation",
    "validate_route_material_lineage",
]
