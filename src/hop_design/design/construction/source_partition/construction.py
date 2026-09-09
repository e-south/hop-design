"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/source_partition/construction.py

Searches source-removal programs for one explicitly selected construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path

from hop_design.design.construction.complete.bundle import (
    ConstructionCompilation,
    VerifiedConstructionBundle,
)
from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.complete.source_partition.facts import route_fragment_fact
from hop_design.models.construction.complete.state import ConstructionStatePhase
from hop_design.models.construction.payload import PayloadSourceMap, PayloadSourceSegment
from hop_design.models.construction.source_partition.request import (
    ConstructionSourcePartitionPolicy,
    SourceDuplexMaterial,
    SourcePartitionConstraints,
    SourcePartitionDiscoveryRequest,
    SourcePartitionSurvivor,
)
from hop_design.models.coordinates import Boundary, Span

from .discovery import discover_source_partitions
from .public import SourcePartitionDiscovery


def discover_construction_source_partition(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
    policy_path: str | Path,
    *,
    materialized_realization_id: str,
) -> SourcePartitionDiscovery:
    """Search exact length-based source removal without changing the selected route."""
    if not isinstance(receipt, ConstructionCompilation | VerifiedConstructionBundle):
        raise TypeError("Source-removal discovery requires a verified construction receipt.")
    result = receipt._verified_source().result
    realization = next(
        (
            item
            for item in result.realizations
            if item.materialized_realization_id == materialized_realization_id
        ),
        None,
    )
    if realization is None:
        raise ValueError("Source-removal selection is not an accepted construction realization.")
    mapping = load_source_mapping(policy_path, source_label="HOP source-partition policy")
    if mapping.get("schema") != "hop.source-partition-policy/v1":
        raise ValueError(
            f"Unsupported HOP source-partition policy schema: {mapping.get('schema')!r}."
        )
    policy = ConstructionSourcePartitionPolicy.model_validate_json(json.dumps(mapping))
    preparation = realization.source_preparation
    top, bottom = (item.material for item in preparation.produced_material_bindings)
    selected = next(
        state
        for state in realization.construction_program.states
        if state.phase is ConstructionStatePhase.SELECTED_FRAGMENTS
    )
    facts = tuple(
        route_fragment_fact(
            strand,
            source_length=len(top.sequence_5prime),
            top_use_id=preparation.prepared_top_use.use_id,
            bottom_use_id=preparation.prepared_bottom_use.use_id,
        )
        for strand in selected.molecules
    )
    source_id = "source-duplex"
    request = SourcePartitionDiscoveryRequest(
        payload=result.request.payload,
        source=SourceDuplexMaterial(
            material_id=source_id,
            top_sequence_5prime=top.sequence_5prime,
            top_five_prime_end=top.five_prime_end,
            top_three_prime_end=top.three_prime_end,
            bottom_five_prime_end=bottom.five_prime_end,
            bottom_three_prime_end=bottom.three_prime_end,
        ),
        payload_source_map=PayloadSourceMap(
            segments=tuple(
                PayloadSourceSegment(
                    payload_span=segment.payload_span,
                    source_material_id=source_id,
                    source_span=segment.source_span,
                    orientation=segment.orientation,
                )
                for segment in realization.payload_source_map.segments
            )
        ),
        enzyme_provisioning=policy.enzyme_provisioning,
        constraints=SourcePartitionConstraints(
            fragment_policy=policy.fragment_policy,
            max_enzymes_per_program=policy.max_enzymes_per_program,
            required_survivors=tuple(
                SourcePartitionSurvivor(
                    survivor_id=f"required-{fact.strand.value}-{fact.start}-{fact.end}",
                    precursor_strand=fact.strand,
                    source_span=Span(
                        start=Boundary(offset=fact.start), end=Boundary(offset=fact.end)
                    ),
                )
                for fact in facts
            ),
        ),
        enumeration=policy.enumeration,
    )
    return SourcePartitionDiscovery._create(discover_source_partitions(request))


__all__ = ["discover_construction_source_partition"]
