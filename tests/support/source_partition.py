"""
--------------------------------------------------------------------------------
HOP Design
tests/support/source_partition.py

Builds exact source-partition fixtures from materialized complete routes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterable

from hop_design.design.construction.source_partition import discover_source_partitions
from hop_design.models.construction.complete import ConstructionStatePhase
from hop_design.models.construction.payload import PayloadSourceMap, PayloadSourceSegment
from hop_design.models.construction.source_partition import (
    SourceDuplexMaterial,
    SourcePartitionConstraints,
    SourcePartitionDiscoveryRequest,
    SourcePartitionEnumerationPolicy,
    SourcePartitionSurvivor,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    CharacterizedEnzymeCatalog,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    EnzymeRoleRestriction,
)
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import FragmentLengthSelection, LineageStrand


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _source_fact(realization, molecule) -> tuple[Strand, Span]:
    source_length = len(realization.materials[0].sequence_5prime)
    indexes = tuple(item.origin_index for item in molecule.lineage)
    origin_ids = {item.origin_id for item in molecule.lineage}
    origin_strands = {item.origin_strand for item in molecule.lineage}
    if origin_ids == {realization.material_uses[0].use_id} and origin_strands == {
        LineageStrand.PRIMARY
    }:
        strand = Strand.TOP
        start, end = min(indexes), max(indexes) + 1
    elif origin_ids == {realization.material_uses[1].use_id} and origin_strands == {
        LineageStrand.COMPLEMENTARY
    }:
        strand = Strand.BOTTOM
        start = source_length - max(indexes) - 1
        end = source_length - min(indexes)
    else:
        raise ValueError("Source-partition fixture requires one exact source lineage per strand.")
    if tuple(range(min(indexes), max(indexes) + 1)) != indexes:
        raise ValueError("Source-partition fixture requires contiguous source lineage.")
    return strand, _span(start, end)


def source_partition_for_route(
    *,
    payload,
    realization,
    enzymes: Iterable[CharacterizedEnzyme],
):
    """Discover the inclusive length partition already expressed by one route."""
    enzyme_domain = tuple(enzymes)
    denatured = next(
        item
        for item in realization.construction_program.states
        if item.phase is ConstructionStatePhase.DENATURED_FRAGMENTS
    )
    selected = next(
        item
        for item in realization.construction_program.states
        if item.phase is ConstructionStatePhase.SELECTED_FRAGMENTS
    )
    selected_facts = tuple(_source_fact(realization, item) for item in selected.molecules)
    selected_lengths = tuple(len(item.sequence) for item in selected.molecules)
    selected_fact_set = set(selected_facts)
    excluded_lengths = tuple(
        len(item.sequence)
        for item in denatured.molecules
        if _source_fact(realization, item) not in selected_fact_set
    )
    threshold = min(selected_lengths)
    if excluded_lengths and max(excluded_lengths) >= threshold:
        raise ValueError("The route fragment selection is not an inclusive length partition.")
    source = realization.source_preparation.source_ssdna
    source_id = "source-duplex"
    source_map = PayloadSourceMap(
        segments=tuple(
            PayloadSourceSegment(
                payload_span=item.payload_span,
                source_material_id=source_id,
                source_span=item.source_span,
                orientation=item.orientation,
            )
            for item in realization.payload_source_map.segments
        )
    )
    request = SourcePartitionDiscoveryRequest(
        payload=payload,
        source=SourceDuplexMaterial(
            material_id=source_id,
            top_sequence_5prime=source.sequence_5prime,
            top_five_prime_end=realization.materials[0].five_prime_end,
            top_three_prime_end=realization.materials[0].three_prime_end,
            bottom_five_prime_end=realization.materials[1].five_prime_end,
            bottom_three_prime_end=realization.materials[1].three_prime_end,
        ),
        payload_source_map=source_map,
        enzyme_provisioning=EnzymeProvisioningPolicy(
            catalog=CharacterizedEnzymeCatalog(
                catalog_id="example:enzyme-catalog/route-partition@1",
                enzymes=enzyme_domain,
            ),
            allowed_enzyme_ids=tuple(item.enzyme_id for item in enzyme_domain),
            forbidden_enzyme_ids=(),
            reserved_enzyme_ids=(),
            max_operations=max(1, len(enzyme_domain)),
            role_restrictions=(
                EnzymeRoleRestriction(
                    role=EnzymeRole.STRAND_EXPOSURE,
                    allowed_enzyme_ids=tuple(item.enzyme_id for item in enzyme_domain),
                ),
            ),
        ),
        constraints=SourcePartitionConstraints(
            selection=FragmentLengthSelection(min_length_nt=threshold),
            required_survivors=tuple(
                SourcePartitionSurvivor(
                    survivor_id=(f"required-{strand.value}-{span.start.offset}-{span.end.offset}"),
                    precursor_strand=strand,
                    source_span=span,
                )
                for strand, span in selected_facts
            ),
            max_enzymes_per_program=len(enzyme_domain),
        ),
        enumeration=SourcePartitionEnumerationPolicy(
            max_search_nodes=(2 ** len(enzyme_domain)) - 1,
            max_realizations=(2 ** len(enzyme_domain)) - 1,
        ),
    )
    return discover_source_partitions(request)


__all__ = ["source_partition_for_route"]
