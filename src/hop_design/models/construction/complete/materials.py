"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/materials.py

Validates complete-route source states against exact material authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from hop_design.models.construction.payload import SourceOrientation
from hop_design.models.molecular_state import EndChemistry, Fragment, LineageStrand
from hop_design.models.physical import Strand, classify_literal_pair
from hop_design.models.reactions import ReactionMolecule

from .evaluation_inputs import LinearSourceEmbedding
from .material import ExactConstructionMaterial
from .state import ConstructionState, ConstructionStatePhase


@dataclass(frozen=True, slots=True)
class MaterialOccurrence:
    """Exact material span and terminal chemistry for one reaction strand."""

    start: int
    length: int
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry
    origin_strand: LineageStrand


def _embedded_fragment_occurrence(
    *,
    fragment: Fragment,
    embedding: LinearSourceEmbedding,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
    include_periphery: bool = True,
) -> MaterialOccurrence:
    local_start = fragment.precursor_span.start.offset
    local_end = fragment.precursor_span.end.offset
    local_length = embedding.local_source_length
    if fragment.precursor_strand is Strand.TOP:
        start = embedding.local_reference_offset + local_start
        end = embedding.local_reference_offset + local_end
        if include_periphery and local_start == 0:
            start = 0
        if include_periphery and local_end == local_length:
            end = len(source.sequence_5prime)
        material = source
        origin_strand = LineageStrand.PRIMARY
    else:
        start = embedding.local_complement_offset + local_length - local_end
        end = embedding.local_complement_offset + local_length - local_start
        if include_periphery and local_end == local_length:
            start = 0
        if include_periphery and local_start == 0:
            end = len(source_complement.sequence_5prime)
        material = source_complement
        origin_strand = LineageStrand.COMPLEMENTARY
    return MaterialOccurrence(
        start=start,
        length=end - start,
        five_prime_end=(material.five_prime_end if start == 0 else fragment.five_prime_end),
        three_prime_end=(
            material.three_prime_end
            if end == len(material.sequence_5prime)
            else fragment.three_prime_end
        ),
        origin_strand=origin_strand,
    )


def foldback_occurrences(
    molecules: tuple[ReactionMolecule, ...],
    *,
    fragments: tuple[Fragment, ...],
    embedding: LinearSourceEmbedding,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> dict[str, tuple[MaterialOccurrence, MaterialOccurrence | None]]:
    """Resolve reaction strands from exact local fragment coordinates."""
    local_source_length = embedding.local_source_length
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
            reference = MaterialOccurrence(
                start=0,
                length=len(source.sequence_5prime),
                five_prime_end=source.five_prime_end,
                three_prime_end=source.three_prime_end,
                origin_strand=LineageStrand.PRIMARY,
            )
            complement = None
            if molecule.complement_sequence_5prime is not None:
                complement = MaterialOccurrence(
                    start=0,
                    length=len(source_complement.sequence_5prime),
                    five_prime_end=source_complement.five_prime_end,
                    three_prime_end=source_complement.three_prime_end,
                    origin_strand=LineageStrand.COMPLEMENTARY,
                )
        elif molecule.molecule_id == "released-duplex" or molecule.molecule_id.endswith(
            "-released-duplex"
        ):
            local_start = local_source_length - len(molecule.reference_sequence_5prime)
            top = fragments_by_span[(Strand.TOP, local_start, local_source_length)]
            bottom = fragments_by_span[(Strand.BOTTOM, local_start, local_source_length)]
            reference = _embedded_fragment_occurrence(
                fragment=top,
                embedding=embedding,
                source=source,
                source_complement=source_complement,
                include_periphery=False,
            )
            complement = (
                None
                if molecule.complement_sequence_5prime is None
                else _embedded_fragment_occurrence(
                    fragment=bottom,
                    embedding=embedding,
                    source=source,
                    source_complement=source_complement,
                    include_periphery=False,
                )
            )
        else:
            if molecule.molecule_id.endswith(("-pcr-bottom-retained", "-pcr-top-retained")):
                strand_prefix = (
                    "bottom-" if molecule.molecule_id.endswith("-pcr-bottom-retained") else "top-"
                )
                fragment = next(
                    item
                    for fragment_id, item in fragments_by_id.items()
                    if fragment_id.startswith(strand_prefix) and fragment_id in molecule.molecule_id
                )
                occurrence = _embedded_fragment_occurrence(
                    fragment=fragment,
                    embedding=embedding,
                    source=source,
                    source_complement=source_complement,
                    include_periphery=False,
                )
                occurrences[molecule.molecule_id] = (
                    replace(occurrence, length=len(molecule.reference_sequence_5prime)),
                    None,
                )
                continue
            if molecule.molecule_id.endswith(
                ("-pcr-bottom-source-return-arm", "-pcr-top-source-return-arm")
            ):
                if molecule.molecule_id.endswith("-pcr-bottom-source-return-arm"):
                    if embedding.source_orientation is not SourceOrientation.FORWARD:
                        raise ValueError(
                            "PCR bottom source-return replay requires a forward source embedding."
                        )
                    material = source_complement
                    origin_strand = LineageStrand.COMPLEMENTARY
                else:
                    if embedding.source_orientation is not SourceOrientation.REVERSE_COMPLEMENT:
                        raise ValueError(
                            "PCR top source-return replay requires a reverse source embedding."
                        )
                    material = source
                    origin_strand = LineageStrand.PRIMARY
                start = len(material.sequence_5prime) - len(molecule.reference_sequence_5prime)
                occurrences[molecule.molecule_id] = (
                    MaterialOccurrence(
                        start=start,
                        length=len(material.sequence_5prime) - start,
                        five_prime_end=EndChemistry.PHOSPHATE,
                        three_prime_end=material.three_prime_end,
                        origin_strand=origin_strand,
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
            reference = _embedded_fragment_occurrence(
                fragment=matched_fragment,
                embedding=embedding,
                source=source,
                source_complement=source_complement,
            )
            complement = None
        occurrences[molecule.molecule_id] = (reference, complement)
    return occurrences


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
                length=len(source.sequence_5prime),
                five_prime_end=source.five_prime_end,
                three_prime_end=source.three_prime_end,
                origin_strand=LineageStrand.PRIMARY,
            ),
            MaterialOccurrence(
                start=0,
                length=len(source_complement.sequence_5prime),
                five_prime_end=source_complement.five_prime_end,
                three_prime_end=source_complement.three_prime_end,
                origin_strand=LineageStrand.COMPLEMENTARY,
            ),
        )
    return occurrences


def validate_initial_material_state(
    state: ConstructionState,
    materials: tuple[ExactConstructionMaterial, ...],
) -> None:
    """Require the first route state to replay both exact source materials."""
    if len(materials) < 2 or len(state.molecules) != 2:
        raise ValueError("Construction source state requires two exact source strands.")
    if state.phase is not ConstructionStatePhase.DUPLEX or not state.pairings:
        raise ValueError("Construction source state must preserve exact duplex association.")
    expected = (
        (materials[0], LineageStrand.PRIMARY),
        (materials[1], LineageStrand.COMPLEMENTARY),
    )
    for strand, (material, lineage_strand) in zip(state.molecules, expected, strict=True):
        if (
            strand.sequence != material.sequence_5prime
            or strand.five_prime_end is not material.five_prime_end
            or strand.three_prime_end is not material.three_prime_end
        ):
            raise ValueError("Construction source state must replay exact material chemistry.")
        if tuple(
            (item.origin_id, item.origin_strand, item.origin_index) for item in strand.lineage
        ) != tuple(
            (material.material_id, lineage_strand, index)
            for index in range(len(material.sequence_5prime))
        ):
            raise ValueError("Construction source state must replay exact material lineage.")
    source_strand, complement_strand = state.molecules
    expected_pairs = {
        (
            source_strand.strand_id,
            index,
            complement_strand.strand_id,
            len(source_strand.sequence) - 1 - index,
            source_strand.sequence[index],
            complement_strand.sequence[len(source_strand.sequence) - 1 - index],
            classify_literal_pair(
                left_base=source_strand.sequence[index],
                right_base=complement_strand.sequence[len(source_strand.sequence) - 1 - index],
            ),
        )
        for index in range(len(source_strand.sequence))
    }
    observed_pairs = {
        (
            item.left_strand_id,
            item.left_index,
            item.right_strand_id,
            item.right_index,
            item.left_base,
            item.right_base,
            item.kind,
        )
        for item in state.pairings
    }
    if observed_pairs != expected_pairs:
        raise ValueError("Construction source state requires complete complement pairing.")


__all__ = [
    "MaterialOccurrence",
    "foldback_occurrences",
    "validate_initial_material_state",
    "whole_source_occurrences",
]
