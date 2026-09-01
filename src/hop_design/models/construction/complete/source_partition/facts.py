"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/facts.py

Projects source, cut, and fragment representations into comparable molecular facts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from hop_design.models.construction.complete.material import (
    ExactConstructionMaterial,
    MaterialUse,
)
from hop_design.models.construction.complete.program import ConstructionProgram
from hop_design.models.construction.complete.source_preparation import (
    SourceDuplexPreparationAuthority,
)
from hop_design.models.construction.payload import FinalPayloadReference, PayloadSourceMap
from hop_design.models.construction.source_partition.result import (
    SourcePartitionDiscoveryResult,
    SourcePartitionRealization,
)
from hop_design.models.enzymes import CharacterizedEnzyme, characterized_enzyme_digest
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import (
    EndChemistry,
    Fragment,
    LineageStrand,
    MolecularStrand,
)
from hop_design.models.reactions import ReactionProgram
from hop_design.models.sequence import reverse_complement_iupac

from .errors import SourcePartitionBindingError, SourcePartitionBindingFailure


@dataclass(frozen=True, slots=True)
class FragmentFact:
    """One strand fragment expressed in source-duplex coordinates."""

    strand: Strand
    start: int
    end: int
    sequence: str
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry


def source_mapping_facts(source_map: PayloadSourceMap) -> tuple[tuple[object, ...], ...]:
    """Project a payload map without representation-specific material identities."""
    return tuple(
        (
            item.payload_span.start.offset,
            item.payload_span.end.offset,
            item.source_span.start.offset,
            item.source_span.end.offset,
            item.orientation,
        )
        for item in source_map.segments
    )


def validate_source_facts(
    *,
    payload: FinalPayloadReference,
    payload_source_map: PayloadSourceMap,
    source_preparation: SourceDuplexPreparationAuthority,
    construction_program: ConstructionProgram,
    materials: tuple[ExactConstructionMaterial, ...],
    material_uses: tuple[MaterialUse, ...],
    partition_result: SourcePartitionDiscoveryResult,
) -> tuple[MaterialUse, MaterialUse]:
    """Require the partition and route to describe the same prepared source duplex."""
    request = partition_result.request
    prepared = source_preparation.produced_material_bindings
    if (
        request.payload.payload_spec_id != payload.payload_spec_id
        or source_mapping_facts(request.payload_source_map)
        != source_mapping_facts(payload_source_map)
        or len(materials) < 2
        or len(material_uses) < 2
        or tuple(item.material for item in prepared) != materials[:2]
        or material_uses[:2]
        != (source_preparation.prepared_top_use, source_preparation.prepared_bottom_use)
        or tuple(item.material_id for item in material_uses[:2])
        != tuple(item.material_id for item in materials[:2])
        or construction_program.states[0] != source_preparation.product_state
    ):
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SOURCE_INCOMPATIBLE,
            "Partition payload, mapping, prepared materials, and route root must agree.",
        )
    top, bottom = materials[:2]
    source = request.source
    if (
        source.top_sequence_5prime != top.sequence_5prime
        or reverse_complement_iupac(source.top_sequence_5prime) != bottom.sequence_5prime
        or source.top_five_prime_end is not top.five_prime_end
        or source.top_three_prime_end is not top.three_prime_end
        or source.bottom_five_prime_end is not bottom.five_prime_end
        or source.bottom_three_prime_end is not bottom.three_prime_end
    ):
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SOURCE_INCOMPATIBLE,
            "Partition source sequence or terminal chemistry differs from the prepared duplex.",
        )
    return material_uses[0], material_uses[1]


def partition_cut_facts(
    result: SourcePartitionDiscoveryResult,
    realization: SourcePartitionRealization,
) -> Counter[tuple[object, ...]]:
    """Project partition nick sites into an exact molecular-fact multiset."""
    return Counter(
        (
            site.agent_id,
            characterized_enzyme_digest(
                result.request.enzyme_provisioning.catalog.by_id(site.agent_id)
            ),
            site.site_span.start.offset,
            site.site_span.end.offset,
            site.orientation,
            site.nick.strand,
            site.nick.boundary.offset,
        )
        for site in realization.nicked_duplex.sites
    )


def route_cut_facts(
    program: ReactionProgram,
    enzyme_definitions: tuple[CharacterizedEnzyme, ...],
) -> Counter[tuple[object, ...]]:
    """Project one concurrent nick stage into the partition cut-fact vocabulary."""
    definitions = {item.enzyme_id: item for item in enzyme_definitions}
    if len(definitions) != len(enzyme_definitions):
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.CUT_INCOMPATIBLE,
            "Route enzyme definitions must use unique enzyme ids.",
        )
    stage = program.stages[0]
    facts: Counter[tuple[object, ...]] = Counter()
    for operation in stage.operations:
        definition = definitions.get(operation.enzyme_id)
        if definition is None:
            raise SourcePartitionBindingError(
                SourcePartitionBindingFailure.CUT_INCOMPATIBLE,
                "Every route nick requires its characterized enzyme definition.",
            )
        binding = operation.intended_binding
        strand = Strand.TOP if binding.reference_cut is not None else Strand.BOTTOM
        boundary = binding.reference_cut or binding.complement_cut
        assert boundary is not None
        facts[
            (
                operation.enzyme_id,
                characterized_enzyme_digest(definition),
                binding.recognition_span.start.offset,
                binding.recognition_span.end.offset,
                binding.orientation,
                strand,
                boundary.offset,
            )
        ] += 1
    return facts


def route_fragment_fact(
    strand: MolecularStrand,
    *,
    source_length: int,
    top_use_id: str,
    bottom_use_id: str,
) -> FragmentFact:
    """Project route lineage into top-oriented source coordinates."""
    origin_ids = {item.origin_id for item in strand.lineage}
    origin_strands = {item.origin_strand for item in strand.lineage}
    origin_indexes = tuple(item.origin_index for item in strand.lineage)
    if not origin_indexes:
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
            "A partition fragment must contain one or more source-derived bases.",
        )
    if origin_ids == {top_use_id} and origin_strands == {LineageStrand.PRIMARY}:
        precursor_strand = Strand.TOP
        start = min(origin_indexes)
        end = max(origin_indexes) + 1
        expected_indexes = tuple(range(start, end))
    elif origin_ids == {bottom_use_id} and origin_strands == {LineageStrand.COMPLEMENTARY}:
        precursor_strand = Strand.BOTTOM
        physical_start = min(origin_indexes)
        physical_end = max(origin_indexes) + 1
        start = source_length - physical_end
        end = source_length - physical_start
        expected_indexes = tuple(range(physical_start, physical_end))
    else:
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
            "A partition fragment must derive wholly from one prepared source strand use.",
        )
    if origin_indexes != expected_indexes:
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
            "A partition fragment must retain contiguous source lineage.",
        )
    return FragmentFact(
        strand=precursor_strand,
        start=start,
        end=end,
        sequence=strand.sequence,
        five_prime_end=strand.five_prime_end,
        three_prime_end=strand.three_prime_end,
    )


def partition_fragment_fact(fragment: Fragment) -> FragmentFact:
    """Project a partition fragment without its representation-specific identifier."""
    return FragmentFact(
        strand=fragment.precursor_strand,
        start=fragment.precursor_span.start.offset,
        end=fragment.precursor_span.end.offset,
        sequence=fragment.sequence,
        five_prime_end=fragment.five_prime_end,
        three_prime_end=fragment.three_prime_end,
    )


__all__ = [
    "FragmentFact",
    "partition_cut_facts",
    "partition_fragment_fact",
    "route_cut_facts",
    "route_fragment_fact",
    "source_mapping_facts",
    "validate_source_facts",
]
