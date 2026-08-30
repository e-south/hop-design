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

from hop_design.design.bundle import load_verified_bundle
from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.complete.bundle import (
    ConstructionCompilation,
    compile_construction_bundle,
)
from hop_design.design.construction.complete.discovery import discover_constructions
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.verification import (
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
from hop_design.models.payload import ExactPayload


def _load_construction_source(path: str | Path) -> ConstructionSource:
    mapping = load_source_mapping(path)
    if mapping.get("schema") != "hop.construction-source/v2":
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
    encoding = design.plan.hairpin_encoding_insert
    request = ConstructionDiscoveryRequest(
        payload=payload,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=source.composition.endpoint,
        foldback_result_id=foldback.result.result_id,
        basal_result_id=None if basal is None else basal.result.result_id,
        materialization=source.composition.materialization,
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
    construction = discover_constructions(
        request,
        foldback=foldback,
        basal=basal,
        design=design,
    )
    return compile_construction_bundle(construction)


__all__ = ["compile_construction_source"]
