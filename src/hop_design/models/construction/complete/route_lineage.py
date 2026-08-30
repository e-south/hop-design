"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/route_lineage.py

Derives complete-route strands from exact local fragment and material coordinates.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import (
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
)
from hop_design.models.reactions import ReactionMolecule

from .evaluation_inputs import LinearSourceEmbedding
from .materials import MaterialOccurrence, foldback_occurrences
from .request import ExactConstructionMaterial


def material_strand(
    strand_id: str,
    material: ExactConstructionMaterial,
    *,
    lineage_strand: LineageStrand,
) -> MolecularStrand:
    """Create one exact strand whose bases map to one declared material."""
    return MolecularStrand(
        strand_id=strand_id,
        sequence=material.sequence_5prime,
        five_prime_end=material.five_prime_end,
        three_prime_end=material.three_prime_end,
        lineage=tuple(
            MaterialBaseLineage(
                product_index=index,
                origin_id=material.material_id,
                origin_strand=lineage_strand,
                origin_index=index,
            )
            for index in range(len(material.sequence_5prime))
        ),
    )


def reaction_molecule_strands(
    molecule: ReactionMolecule,
    *,
    namespace: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
    reference_occurrence: MaterialOccurrence,
    complement_occurrence: MaterialOccurrence | None,
) -> tuple[MolecularStrand, ...]:
    """Map one reaction molecule into exact material coordinates."""
    primary_material = (
        source if reference_occurrence.origin_strand is LineageStrand.PRIMARY else source_complement
    )
    primary_lineage = reference_occurrence.origin_strand
    output = [
        _subsequence_strand(
            f"{namespace}-{molecule.molecule_id}-top",
            molecule.reference_sequence_5prime,
            material=primary_material,
            lineage_strand=primary_lineage,
            occurrence=reference_occurrence,
        )
    ]
    if molecule.complement_sequence_5prime is not None:
        if complement_occurrence is None:
            raise ValueError("A duplex reaction molecule requires exact complement occurrence.")
        output.append(
            _subsequence_strand(
                f"{namespace}-{molecule.molecule_id}-bottom",
                molecule.complement_sequence_5prime,
                material=source_complement,
                lineage_strand=LineageStrand.COMPLEMENTARY,
                occurrence=complement_occurrence,
            )
        )
    return tuple(output)


def lift_reaction_molecules(
    molecules: tuple[ReactionMolecule, ...],
    *,
    foldback: FoldbackLocalRealization,
    embedding: LinearSourceEmbedding,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> tuple[ReactionMolecule, ...]:
    """Lift local reaction molecules into their exact complete-source coordinates."""
    occurrences = foldback_occurrences(
        molecules,
        fragments=foldback.molecular_fragments,
        embedding=embedding,
        source=source,
        source_complement=source_complement,
    )
    lifted: list[ReactionMolecule] = []
    for molecule in molecules:
        reference_occurrence, complement_occurrence = occurrences[molecule.molecule_id]
        reference_material = (
            source
            if reference_occurrence.origin_strand is LineageStrand.PRIMARY
            else source_complement
        )
        reference = reference_material.sequence_5prime[
            reference_occurrence.start : reference_occurrence.start + reference_occurrence.length
        ]
        complement = None
        if complement_occurrence is not None:
            complement_material = (
                source
                if complement_occurrence.origin_strand is LineageStrand.PRIMARY
                else source_complement
            )
            complement = complement_material.sequence_5prime[
                complement_occurrence.start : complement_occurrence.start
                + complement_occurrence.length
            ]
        lifted.append(
            ReactionMolecule(
                molecule_id=molecule.molecule_id,
                reference_sequence_5prime=reference,
                complement_sequence_5prime=complement,
            )
        )
    return tuple(lifted)


def _subsequence_strand(
    strand_id: str,
    sequence: str,
    *,
    material: ExactConstructionMaterial,
    lineage_strand: LineageStrand,
    occurrence: MaterialOccurrence,
) -> MolecularStrand:
    start = occurrence.start
    end = start + occurrence.length
    if start < 0 or end > len(material.sequence_5prime):
        raise ValueError("Reaction-state occurrence must lie within its exact material.")
    if occurrence.length != len(sequence):
        raise ValueError("Reaction-state occurrence length must match the exact molecule.")
    if material.sequence_5prime[start:end] != sequence:
        raise ValueError(
            "Reaction-state occurrence must replay the exact material bytes: "
            f"{sequence!r} != {material.sequence_5prime[start:end]!r}."
        )
    return MolecularStrand(
        strand_id=strand_id,
        sequence=sequence,
        five_prime_end=occurrence.five_prime_end,
        three_prime_end=occurrence.three_prime_end,
        lineage=tuple(
            MaterialBaseLineage(
                product_index=index,
                origin_id=material.material_id,
                origin_strand=lineage_strand,
                origin_index=start + index,
            )
            for index in range(len(sequence))
        ),
    )


def derive_post_cleavage_strands(
    molecules: tuple[ReactionMolecule, ...],
    *,
    namespace: str,
    foldback: FoldbackLocalRealization,
    embedding: LinearSourceEmbedding,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> tuple[MolecularStrand, ...]:
    """Derive every exact post-cleavage strand from local fragment spans."""
    occurrences = foldback_occurrences(
        molecules,
        fragments=foldback.molecular_fragments,
        embedding=embedding,
        source=source,
        source_complement=source_complement,
    )
    strands = tuple(
        strand
        for molecule in molecules
        for strand in reaction_molecule_strands(
            molecule,
            namespace=namespace,
            source=source,
            source_complement=source_complement,
            reference_occurrence=occurrences[molecule.molecule_id][0],
            complement_occurrence=occurrences[molecule.molecule_id][1],
        )
    )
    return strands


__all__ = [
    "derive_post_cleavage_strands",
    "lift_reaction_molecules",
    "material_strand",
    "reaction_molecule_strands",
]
