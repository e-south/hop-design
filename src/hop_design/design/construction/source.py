"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/source.py

Compiles one strict construction source against a separate verified design authority.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path

from hop_design.design.bundle import VerifiedHopBundle, load_verified_bundle
from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.complete.bundle import (
    ConstructionCompilation,
    compile_construction_bundle,
)
from hop_design.design.construction.complete.discovery import discover_constructions
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.local_public import LocalNeighborhoodDiscovery
from hop_design.design.construction.source_partition import SourcePartitionDiscovery
from hop_design.design.construction.verification import (
    VerifiedBasalNeighborhoodResult,
    VerifiedFoldbackNeighborhoodResult,
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    DesignAuthorityReference,
)
from hop_design.models.construction.complete.local_authority import payload_space_contains
from hop_design.models.construction.payload import FinalPayloadReference, RouteFamily
from hop_design.models.construction.source import ConstructionSource
from hop_design.models.construction.source_partition import SourcePartitionDiscoveryResult
from hop_design.models.payload import ExactPayload
from hop_design.serialization import canonical_json_bytes


def _load_construction_source(path: str | Path) -> ConstructionSource:
    mapping = load_source_mapping(path)
    if mapping.get("schema") != "hop.construction-source/v6":
        raise ValueError(f"Unsupported HOP construction source schema: {mapping.get('schema')!r}.")
    return ConstructionSource.model_validate_json(json.dumps(mapping, separators=(",", ":")))


def _exact_payload(source: ConstructionSource, sequence: str) -> FinalPayloadReference:
    authored = source.foldback.payload
    if not payload_space_contains(
        authored=authored.payload.sequence,
        exact=sequence,
    ):
        raise ValueError(
            "The verified design payload does not belong to the authored payload space."
        )
    if source.basal is not None and not payload_space_contains(
        authored=source.basal.payload.payload.sequence,
        exact=sequence,
    ):
        raise ValueError("The verified design payload does not belong to the basal payload space.")
    return FinalPayloadReference(
        display_name=authored.display_name,
        payload=ExactPayload(sequence=sequence),
        basal_boundary=authored.basal_boundary,
        foldback_boundary=authored.foldback_boundary,
        pair_state_exceptions=authored.pair_state_exceptions,
    )


def _construction_request(
    *,
    source: ConstructionSource,
    design: VerifiedHopBundle,
    payload: FinalPayloadReference,
    foldback: VerifiedFoldbackNeighborhoodResult,
    basal: VerifiedBasalNeighborhoodResult | None,
    selected_foldback_realization_id: str | None = None,
    selected_basal_realization_id: str | None = None,
    source_partition: SourcePartitionDiscoveryResult | None = None,
    source_partition_realization_id: str | None = None,
) -> ConstructionDiscoveryRequest:
    encoding = design.plan.hairpin_encoding_insert
    return ConstructionDiscoveryRequest(
        payload=payload,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=source.composition.endpoint,
        foldback_result_id=foldback.result.result_id,
        basal_result_id=None if basal is None else basal.result.result_id,
        selected_foldback_realization_id=selected_foldback_realization_id,
        selected_basal_realization_id=selected_basal_realization_id,
        source_partition_result_id=(
            None if source_partition is None else source_partition.result_id
        ),
        selected_source_partition_realization_id=source_partition_realization_id,
        materialization=source.composition.materialization,
        release=source.composition.release,
        design=DesignAuthorityReference(
            bundle=design.bundle,
            spec=design.spec,
            plan=design.plan,
            plan_id=design.plan.plan_id,
            design_id=design.plan.design_id,
            payload_sequence=payload.payload.sequence,
            encoding_sequence=encoding.sequence,
            encoding_digest=encoding.sequence_digest,
        ),
        whole_route_constraints=source.composition.whole_route_constraints,
        enumeration=source.composition.enumeration,
    )


def _compile_verified_authorities(
    *,
    source: ConstructionSource,
    design: VerifiedHopBundle,
    payload: FinalPayloadReference,
    foldback: VerifiedFoldbackNeighborhoodResult,
    basal: VerifiedBasalNeighborhoodResult | None,
    selected_foldback_realization_id: str | None = None,
    selected_basal_realization_id: str | None = None,
    source_partition: SourcePartitionDiscoveryResult | None = None,
    source_partition_realization_id: str | None = None,
) -> ConstructionCompilation:
    request = _construction_request(
        source=source,
        design=design,
        payload=payload,
        foldback=foldback,
        basal=basal,
        selected_foldback_realization_id=selected_foldback_realization_id,
        selected_basal_realization_id=selected_basal_realization_id,
        source_partition=source_partition,
        source_partition_realization_id=source_partition_realization_id,
    )
    construction = discover_constructions(
        request,
        foldback=foldback,
        basal=basal,
        design=design,
        source_partition=source_partition,
    )
    return compile_construction_bundle(construction)


def compile_construction_source(
    source_path: str | Path,
    *,
    design_bundle_path: str | Path,
) -> ConstructionCompilation:
    """Compile one source document through verified local and complete authorities."""
    source = _load_construction_source(source_path)
    design = load_verified_bundle(design_bundle_path)
    payload = _exact_payload(source, design.spec.payload.sequence)

    foldback = verify_foldback_neighborhood_result(discover_foldback_neighborhood(source.foldback))
    basal = (
        None
        if source.basal is None
        else verify_basal_neighborhood_result(discover_basal_neighborhood(source.basal))
    )
    return _compile_verified_authorities(
        source=source,
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
    )


def compile_construction_source_from_local_realizations(
    source_path: str | Path,
    *,
    design_bundle_path: str | Path,
    foldback: LocalNeighborhoodDiscovery,
    foldback_realization_id: str,
    basal: LocalNeighborhoodDiscovery | None = None,
    basal_realization_id: str | None = None,
    source_partition: SourcePartitionDiscovery | None = None,
    source_partition_realization_id: str | None = None,
) -> ConstructionCompilation:
    """Compile one endpoint-complete selection from verified local authorities."""
    if not isinstance(foldback, LocalNeighborhoodDiscovery):
        raise TypeError("Selected composition requires replay-verified local receipts.")
    if (basal is None) != (basal_realization_id is None):
        raise ValueError("Selected basal evidence requires both receipt and realization id.")
    if basal is not None and not isinstance(basal, LocalNeighborhoodDiscovery):
        raise TypeError("Selected composition requires replay-verified local receipts.")
    if (source_partition is None) != (source_partition_realization_id is None):
        raise ValueError("Selected source partition requires both its receipt and realization id.")
    if source_partition is not None and not isinstance(source_partition, SourcePartitionDiscovery):
        raise TypeError("Selected source partition requires a replay-verified receipt.")
    source = _load_construction_source(source_path)
    if source.basal is None and basal is not None:
        raise ValueError("Direct selected construction must omit basal evidence.")
    if source.basal is not None and basal is None:
        raise ValueError("PCR-bearing selected construction requires basal evidence.")
    verified_foldback = foldback._verified_authority()
    verified_basal = None if basal is None else basal._verified_authority()
    verified_source_partition = (
        None if source_partition is None else source_partition._verified_source()
    )
    if not isinstance(verified_foldback, VerifiedFoldbackNeighborhoodResult):
        raise ValueError("The selected foldback receipt has the wrong local family.")
    if verified_basal is not None and not isinstance(
        verified_basal, VerifiedBasalNeighborhoodResult
    ):
        raise ValueError("The selected basal receipt has the wrong local family.")
    if canonical_json_bytes(source.foldback) != canonical_json_bytes(
        verified_foldback.result.neighborhood.request
    ):
        raise ValueError("The foldback receipt does not derive from the construction source.")
    if verified_basal is not None and canonical_json_bytes(source.basal) != canonical_json_bytes(
        verified_basal.result.discovery.request
    ):
        raise ValueError("The basal receipt does not derive from the construction source.")

    design = load_verified_bundle(design_bundle_path)
    payload = _exact_payload(source, design.spec.payload.sequence)
    return _compile_verified_authorities(
        source=source,
        payload=payload,
        foldback=verified_foldback,
        basal=verified_basal,
        design=design,
        selected_foldback_realization_id=foldback_realization_id,
        selected_basal_realization_id=basal_realization_id,
        source_partition=verified_source_partition,
        source_partition_realization_id=source_partition_realization_id,
    )


__all__ = [
    "compile_construction_source",
    "compile_construction_source_from_local_realizations",
]
