"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/evaluation/context.py

Prepares exact source inputs before endpoint-specific evaluation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.enzymes import EnzymeProvisioningPolicy
from hop_design.models.sequence import reverse_complement_iupac

from ..basal_embedding import basal_source_offset
from ..composition_domain import validate_source_context
from ..evaluation_inputs import (
    derive_complete_payload_source_span,
    derive_endpoint_source_return_arm,
    derive_linear_source_embedding,
    derive_route_prefix,
    replay_linear_source_embedding,
)
from ..material import ExactConstructionMaterial
from ..provisioning import merge_provisioning_policies
from ..request import ConstructionDiscoveryRequest
from ..source_preparation import (
    SourceDuplexPreparationAuthority,
    SourcePreparationResolutionError,
    resolve_route_source_preparation,
)
from ..source_preparation.policy import FixedSourceSsdnaPolicy
from .result import CombinationEvaluation, CompositionRejectionCode


@dataclass(frozen=True, slots=True)
class CombinationContext:
    """Caller authorities and fixed accounting for one exact combination."""

    request: ConstructionDiscoveryRequest
    foldback: FoldbackLocalRealization
    basal: BasalRealizationRecord | None
    foldback_policy: EnzymeProvisioningPolicy
    basal_policy: EnzymeProvisioningPolicy | None
    candidate_enzyme_programs: int
    recognition_placements_attempted: int
    constraint_systems_attempted: int
    source_context_sequence: str | None


@dataclass(frozen=True, slots=True)
class PreparedContext:
    """Route-neutral exact source state admitted to endpoint evaluation."""

    combination: CombinationContext
    prefix: str
    source_return_arm: str
    source: ExactConstructionMaterial
    source_complement: ExactConstructionMaterial
    source_preparation: SourceDuplexPreparationAuthority
    pcr_core_sequence: str
    pcr_bearing: bool


def build_combination_context(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord | None,
    foldback_policy: EnzymeProvisioningPolicy,
    basal_policy: EnzymeProvisioningPolicy | None,
    source_context_sequence: str | None,
) -> CombinationContext:
    """Bind one combination and its stable intrinsic-accounting counters."""
    return CombinationContext(
        request=request,
        foldback=foldback,
        basal=basal,
        foldback_policy=foldback_policy,
        basal_policy=basal_policy,
        candidate_enzyme_programs=1 + (0 if basal is None else len(basal.reaction_programs)),
        recognition_placements_attempted=len(foldback.enzyme_bindings)
        + (0 if basal is None else len(basal.enzyme_bindings)),
        constraint_systems_attempted=2 + (0 if basal is None else 1),
        source_context_sequence=source_context_sequence,
    )


def prepare_context(
    context: CombinationContext,
) -> PreparedContext | CombinationEvaluation:
    """Run the route-neutral source-map and source-preparation gates in order."""
    request = context.request
    foldback = context.foldback
    basal = context.basal
    prefix = derive_route_prefix(request, basal, foldback.payload_sequence)
    if prefix is None:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.BASAL_SOURCE_MAP_INCOMPATIBLE,
            candidate_enzyme_programs=context.candidate_enzyme_programs,
            recognition_placements_attempted=context.recognition_placements_attempted,
            constraint_systems_attempted=context.constraint_systems_attempted,
        )
    source_policy = request.materialization.source_preparation.source_ssdna
    validate_source_context(source_policy, context.source_context_sequence)
    if context.source_context_sequence is not None:
        prefix = context.source_context_sequence + prefix
    if basal is not None and isinstance(source_policy, FixedSourceSsdnaPolicy):
        try:
            sequence = source_policy.material.sequence_5prime
            prefix, _, _ = replay_linear_source_embedding(
                foldback=foldback,
                source_sequence=sequence,
                complement_sequence=reverse_complement_iupac(sequence),
            )
            basal_source_offset(basal, prefix)
        except ValueError:
            return CombinationEvaluation(
                rejection_reason=CompositionRejectionCode.SOURCE_PREPARATION_INCOMPATIBLE,
                candidate_enzyme_programs=context.candidate_enzyme_programs,
                recognition_placements_attempted=context.recognition_placements_attempted,
                constraint_systems_attempted=context.constraint_systems_attempted,
            )
    source_return_arm = derive_endpoint_source_return_arm(request, prefix=prefix)
    embedding = derive_linear_source_embedding(
        foldback=foldback,
        prefix=prefix,
        source_return_arm=source_return_arm,
    )
    payload_source_span = derive_complete_payload_source_span(
        foldback=foldback,
        embedding=embedding,
    )
    try:
        source_preparation = resolve_route_source_preparation(
            policy=request.materialization.source_preparation,
            source_sequence=embedding.source_sequence,
            expected_complement_sequence=embedding.complement_sequence,
            payload_source_span=payload_source_span,
            material_requirements=foldback.material_requirements,
        )
    except SourcePreparationResolutionError:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.SOURCE_PREPARATION_INCOMPATIBLE,
            prefix=prefix,
            source_return_arm=source_return_arm,
            candidate_enzyme_programs=context.candidate_enzyme_programs,
            recognition_placements_attempted=context.recognition_placements_attempted,
            constraint_systems_attempted=context.constraint_systems_attempted,
        )
    source, source_complement = tuple(
        binding.material for binding in source_preparation.produced_material_bindings
    )
    pcr_bearing = request.endpoint in {
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    }
    return PreparedContext(
        combination=context,
        prefix=prefix,
        source_return_arm=source_return_arm,
        source=source,
        source_complement=source_complement,
        source_preparation=source_preparation,
        pcr_core_sequence=prefix + foldback.retained_sequence,
        pcr_bearing=pcr_bearing,
    )


def provisioning_policies(
    context: PreparedContext,
) -> tuple[EnzymeProvisioningPolicy, ...]:
    """Bind policies only after endpoint-specific intrinsic gates have passed."""
    combination = context.combination
    if combination.basal is None:
        return (combination.foldback_policy,)
    if combination.basal_policy is None:
        raise ValueError("Basal composition requires its exact provisioning policy.")
    return (combination.foldback_policy, combination.basal_policy)


def merged_provisioning_policy(context: PreparedContext) -> EnzymeProvisioningPolicy:
    """Return the exact merged policy for the prepared route authorities."""
    return merge_provisioning_policies(provisioning_policies(context))
