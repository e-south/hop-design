"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material_replay.py

Replays local foldback and source-material facts across complete routes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization

from .evaluation_inputs import replay_linear_source_embedding
from .pairing_replay import annealed_pairings, duplex_pairings
from .program import ConstructionProgram
from .request import ExactConstructionMaterial
from .route_lineage import derive_post_cleavage_strands
from .route_schedule import derive_direct_reaction_program
from .state import ConstructionStatePhase


def validate_route_material_lineage(
    program: ConstructionProgram,
    materials: tuple[ExactConstructionMaterial, ...],
) -> None:
    """Require every state base to retain one exact declared material origin."""
    material_by_id = {item.material_id: item for item in materials}
    for state in program.states:
        for strand in state.molecules:
            for index, lineage in enumerate(strand.lineage):
                material = material_by_id.get(lineage.origin_id)
                if (
                    material is None
                    or lineage.origin_index >= len(material.sequence_5prime)
                    or strand.sequence[index] != material.sequence_5prime[lineage.origin_index]
                ):
                    raise ValueError(
                        "Construction-state lineage must replay exact declared material bytes."
                    )


def validate_foldback_annealing(
    program: ConstructionProgram,
    *,
    foldback: FoldbackLocalRealization,
    materials: tuple[ExactConstructionMaterial, ...],
) -> None:
    """Bind the complete annealed complex to exact local foldback evidence."""
    selected = next(
        item for item in program.states if item.phase is ConstructionStatePhase.SELECTED_FRAGMENTS
    )
    annealed = next(
        item for item in program.states if item.phase is ConstructionStatePhase.ANNEALED_COMPLEX
    )
    expected = annealed_pairings(
        selected.molecules,
        foldback=foldback,
        source_id=materials[0].material_id,
        complement_id=materials[1].material_id,
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
) -> None:
    """Replay the global enzyme program and fragments from exact local authorities."""
    source, source_complement = materials[:2]
    prefix, return_arm, embedding = replay_linear_source_embedding(
        foldback=foldback,
        source_sequence=source.sequence_5prime,
        complement_sequence=source_complement.sequence_5prime,
    )
    expected_program = derive_direct_reaction_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        return_arm=return_arm,
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
    )
    expected_released = derive_post_cleavage_strands(
        molecules,
        namespace="foldback-released",
        foldback=foldback,
        embedding=embedding,
        source=source,
        source_complement=source_complement,
    )
    if program.states[1].molecules != expected_product or (
        program.states[2].molecules != expected_released
    ):
        raise ValueError(
            "Post-cleavage strands must replay exact fragment chemistry and lineage coordinates."
        )
    expected_cleaved_pairings = duplex_pairings(
        expected_product,
        source_id=source.material_id,
        complement_id=source_complement.material_id,
        source_length=len(source.sequence_5prime),
    )
    if program.states[1].pairings != expected_cleaved_pairings:
        raise ValueError("Cleaved duplex pairings must replay exact retained material coordinates.")


__all__ = [
    "validate_foldback_annealing",
    "validate_route_derivation",
    "validate_route_material_lineage",
]
