"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/partition_binding.py

Binds selected source-partition evidence to one materialized complete route.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    MaterializedConstructionRealization,
)
from hop_design.models.construction.complete.evaluation import CompositionRejectionCode
from hop_design.models.construction.complete.provisioning import (
    resolve_program_enzyme_definitions,
)
from hop_design.models.construction.complete.source_partition import (
    COMPOSITION_REJECTION_BY_BINDING_FAILURE,
    SourcePartitionBindingError,
    bind_source_partition,
)
from hop_design.models.construction.complete.source_partition.plan import (
    SourcePartitionPlan,
    selected_partition_plan,
)
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.source_partition import SourcePartitionDiscoveryResult
from hop_design.models.enzymes import EnzymeProvisioningPolicy


def source_partition_enzyme_policies(
    foldback: FoldbackNeighborhoodDiscoveryResult,
    basal: BasalNeighborhoodDiscoveryResult | None,
) -> tuple[EnzymeProvisioningPolicy, ...]:
    """Return local provisioning policies used by the pre-hairpin route."""
    return (
        foldback.neighborhood.request.enzyme_provisioning,
        *(() if basal is None else (basal.discovery.request.enzyme_provisioning,)),
    )


@dataclass(frozen=True, slots=True)
class PartitionBindingOutcome:
    """One accepted binding or exact rejected pre-partition candidate."""

    realization: MaterializedConstructionRealization | None
    rejection_reason: CompositionRejectionCode | None
    rejection_candidate: MaterializedConstructionRealization | None


def resolve_partition_plan(
    request: ConstructionDiscoveryRequest,
    authority: SourcePartitionDiscoveryResult | None,
) -> SourcePartitionPlan | None:
    """Require one exact embedded authority whenever the request selects a partition."""
    if not request.selects_source_partition:
        if authority is not None:
            raise ValueError("Unselected construction cannot receive source-partition evidence.")
        return None
    if authority is None:
        raise ValueError("Selected construction requires source-partition evidence.")
    verified = SourcePartitionDiscoveryResult.model_validate(authority.model_dump(mode="python"))
    if verified.result_id != request.source_partition_result_id:
        raise ValueError("Source-partition result identity does not match the request.")
    selected_id = request.selected_source_partition_realization_id
    if selected_id not in {item.realization_id for item in verified.realizations}:
        raise ValueError("The selected source-partition realization was not found.")
    return selected_partition_plan(verified, selected_id)


def bind_partition_to_realization(
    *,
    request: ConstructionDiscoveryRequest,
    realization: MaterializedConstructionRealization,
    authority: SourcePartitionDiscoveryResult | None,
    enzyme_policies: tuple[EnzymeProvisioningPolicy, ...],
) -> PartitionBindingOutcome:
    """Return one resealed route or its exact source-partition rejection code."""
    if authority is None:
        return PartitionBindingOutcome(
            realization=realization,
            rejection_reason=None,
            rejection_candidate=None,
        )
    selected_id = request.selected_source_partition_realization_id
    if selected_id is None:
        raise ValueError("Source-partition authority requires an explicit selected realization.")
    route_enzyme_definitions = resolve_program_enzyme_definitions(
        program=realization.construction_program.reaction_programs[0],
        policies=(*enzyme_policies, authority.request.enzyme_provisioning),
    )
    try:
        binding = bind_source_partition(
            payload=request.payload,
            payload_source_map=realization.payload_source_map,
            source_preparation=realization.source_preparation,
            construction_program=realization.construction_program,
            materials=realization.materials,
            material_uses=realization.material_uses,
            route_enzyme_definitions=route_enzyme_definitions,
            partition_result=authority,
            selected_realization_id=selected_id,
        )
    except SourcePartitionBindingError as exc:
        return PartitionBindingOutcome(
            realization=None,
            rejection_reason=COMPOSITION_REJECTION_BY_BINDING_FAILURE[exc.code],
            rejection_candidate=realization,
        )
    content = {
        name: getattr(realization, name)
        for name in MaterializedConstructionRealization.model_fields
        if name != "materialized_realization_id"
    }
    content["source_partition_binding"] = binding
    return PartitionBindingOutcome(
        realization=MaterializedConstructionRealization.create(**content),
        rejection_reason=None,
        rejection_candidate=None,
    )


__all__ = [
    "PartitionBindingOutcome",
    "bind_partition_to_realization",
    "resolve_partition_plan",
    "source_partition_enzyme_policies",
]
