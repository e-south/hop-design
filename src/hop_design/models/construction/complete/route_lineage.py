"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/route_lineage.py

Derives complete-route strands from exact local fragment and material coordinates.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import (
    EndChemistry,
    Fragment,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
)
from hop_design.models.physical import Strand
from hop_design.models.reactions import ReactionMolecule

from .request import ExactConstructionMaterial


@dataclass(frozen=True, slots=True)
class MaterialOccurrence:
    """Exact material span and terminal chemistry for one reaction strand."""

    start: int
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry


def foldback_occurrences(
    molecules: tuple[ReactionMolecule, ...],
    *,
    fragments: tuple[Fragment, ...],
    prefix_length: int,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> dict[str, tuple[MaterialOccurrence, MaterialOccurrence | None]]:
    """Resolve reaction strands from exact local fragment coordinates."""
    local_source_length = len(source.sequence_5prime) - prefix_length
    full_length = len(source.sequence_5prime)
    fragments_by_id = {item.fragment_id: item for item in fragments}
    fragments_by_span = {
        (
            item.precursor_strand,
            item.precursor_span.start.offset,
            item.precursor_span.end.offset,
        ): item
        for item in fragments
    }
    occurrences: dict[str, tuple[MaterialOccurrence, MaterialOccurrence | None]] = {}
    for molecule in molecules:
        local_id = molecule.molecule_id.rsplit("-", maxsplit=1)[-1]
        if molecule.molecule_id.endswith("-source") or local_id == "source":
            local_end = len(molecule.reference_sequence_5prime) - prefix_length
            top = fragments_by_span.get((Strand.TOP, 0, local_end))
            bottom = fragments_by_span.get((Strand.BOTTOM, 0, local_end))
            reference = MaterialOccurrence(
                start=0,
                five_prime_end=source.five_prime_end if top is None else top.five_prime_end,
                three_prime_end=source.three_prime_end if top is None else top.three_prime_end,
            )
            complement = None
            if molecule.complement_sequence_5prime is not None:
                complement = MaterialOccurrence(
                    start=full_length - len(molecule.complement_sequence_5prime),
                    five_prime_end=(
                        source_complement.five_prime_end
                        if bottom is None
                        else bottom.five_prime_end
                    ),
                    three_prime_end=(
                        source_complement.three_prime_end
                        if bottom is None
                        else bottom.three_prime_end
                    ),
                )
        elif molecule.molecule_id.endswith("-released-duplex") or local_id == "released-duplex":
            local_start = local_source_length - len(molecule.reference_sequence_5prime)
            top = fragments_by_span[(Strand.TOP, local_start, local_source_length)]
            bottom = fragments_by_span[(Strand.BOTTOM, local_start, local_source_length)]
            reference = MaterialOccurrence(
                start=prefix_length + local_start,
                five_prime_end=top.five_prime_end,
                three_prime_end=top.three_prime_end,
            )
            complement = (
                None
                if molecule.complement_sequence_5prime is None
                else MaterialOccurrence(
                    start=0,
                    five_prime_end=bottom.five_prime_end,
                    three_prime_end=bottom.three_prime_end,
                )
            )
        else:
            if molecule.molecule_id.endswith("-pcr-bottom-retained"):
                fragment = next(
                    item
                    for fragment_id, item in fragments_by_id.items()
                    if fragment_id.startswith("bottom-") and fragment_id in molecule.molecule_id
                )
                occurrences[molecule.molecule_id] = (
                    MaterialOccurrence(
                        start=full_length - (prefix_length + fragment.precursor_span.end.offset),
                        five_prime_end=source_complement.five_prime_end,
                        three_prime_end=EndChemistry.HYDROXYL,
                    ),
                    None,
                )
                continue
            if molecule.molecule_id.endswith("-pcr-bottom-return-arm"):
                occurrences[molecule.molecule_id] = (
                    MaterialOccurrence(
                        start=full_length - prefix_length,
                        five_prime_end=EndChemistry.PHOSPHATE,
                        three_prime_end=source_complement.three_prime_end,
                    ),
                    None,
                )
                continue
            matched_fragment = next(
                (
                    item
                    for fragment_id, item in fragments_by_id.items()
                    if molecule.molecule_id.endswith(fragment_id)
                ),
                None,
            )
            if matched_fragment is None:
                raise ValueError("Foldback reaction molecule lacks an exact fragment authority.")
            source_start = (
                0
                if matched_fragment.precursor_span.start.offset == 0
                else prefix_length + matched_fragment.precursor_span.start.offset
            )
            source_end = prefix_length + matched_fragment.precursor_span.end.offset
            reference_start = (
                source_start
                if matched_fragment.precursor_strand is Strand.TOP
                else full_length - source_end
            )
            reference = MaterialOccurrence(
                start=reference_start,
                five_prime_end=matched_fragment.five_prime_end,
                three_prime_end=matched_fragment.three_prime_end,
            )
            complement = None
        occurrences[molecule.molecule_id] = (reference, complement)
    return occurrences


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


def whole_source_occurrences(
    molecules: tuple[ReactionMolecule, ...],
    *,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> dict[str, tuple[MaterialOccurrence, MaterialOccurrence | None]]:
    """Resolve a reaction state that preserves the complete exact source duplex."""
    occurrences: dict[str, tuple[MaterialOccurrence, MaterialOccurrence | None]] = {}
    for molecule in molecules:
        if molecule.reference_sequence_5prime != source.sequence_5prime or (
            molecule.complement_sequence_5prime != source_complement.sequence_5prime
        ):
            raise ValueError("Basal reaction state must preserve the complete exact source duplex.")
        occurrences[molecule.molecule_id] = (
            MaterialOccurrence(
                start=0,
                five_prime_end=source.five_prime_end,
                three_prime_end=source.three_prime_end,
            ),
            MaterialOccurrence(
                start=0,
                five_prime_end=source_complement.five_prime_end,
                three_prime_end=source_complement.three_prime_end,
            ),
        )
    return occurrences


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
    primary_material = source
    primary_lineage = LineageStrand.PRIMARY
    if molecule.complement_sequence_5prime is None and "bottom-" in molecule.molecule_id:
        primary_material = source_complement
        primary_lineage = LineageStrand.COMPLEMENTARY
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


def _subsequence_strand(
    strand_id: str,
    sequence: str,
    *,
    material: ExactConstructionMaterial,
    lineage_strand: LineageStrand,
    occurrence: MaterialOccurrence,
) -> MolecularStrand:
    start = occurrence.start
    end = start + len(sequence)
    if start < 0 or end > len(material.sequence_5prime):
        raise ValueError("Reaction-state occurrence must lie within its exact material.")
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
    prefix_length: int,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> tuple[MolecularStrand, ...]:
    """Derive every exact post-cleavage strand from local fragment spans."""
    occurrences = foldback_occurrences(
        molecules,
        fragments=foldback.molecular_fragments,
        prefix_length=prefix_length,
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
    "MaterialOccurrence",
    "derive_post_cleavage_strands",
    "foldback_occurrences",
    "material_strand",
    "reaction_molecule_strands",
    "whole_source_occurrences",
]
