"""Replay one complete-route combination in the closed intrinsic gate order."""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.enzymes import EnzymeProvisioningPolicy

from ..request import ConstructionDiscoveryRequest
from .clone import evaluate_clone_endpoint
from .context import PreparedContext, build_combination_context, prepare_context
from .direct import evaluate_direct_endpoint
from .pcr import evaluate_pcr_endpoint
from .result import CombinationEvaluation, CompositionRejectionCode, EndpointEvaluation


def _materialize_evaluation(
    *,
    context: PreparedContext,
    endpoint: EndpointEvaluation,
    rejection_reason: CompositionRejectionCode | None,
) -> CombinationEvaluation:
    combination = context.combination
    return CombinationEvaluation(
        rejection_reason=rejection_reason,
        prefix=context.prefix,
        source_return_arm=context.source_return_arm,
        source=context.source,
        source_complement=context.source_complement,
        source_preparation=context.source_preparation,
        endpoint_auxiliaries=endpoint.endpoint_auxiliaries,
        reaction_program=endpoint.reaction_program,
        stage_assessments=endpoint.stage_assessments,
        end_generation_program=endpoint.end_generation_program,
        end_generation_stage_assessments=endpoint.end_generation_stage_assessments,
        end_generation_bindings=endpoint.end_generation_bindings,
        pcr_template_sequence=endpoint.pcr_template_sequence,
        design_parent_span=endpoint.design_parent_span,
        final_sequence=endpoint.final_sequence,
        candidate_enzyme_programs=combination.candidate_enzyme_programs,
        recognition_placements_attempted=combination.recognition_placements_attempted,
        constraint_systems_attempted=combination.constraint_systems_attempted,
    )


def evaluate_combination(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord | None,
    foldback_policy: EnzymeProvisioningPolicy,
    basal_policy: EnzymeProvisioningPolicy | None,
    source_context_sequence: str | None = None,
) -> CombinationEvaluation:
    """Evaluate one exact combination in the closed intrinsic gate order."""
    combination = build_combination_context(
        request,
        foldback=foldback,
        basal=basal,
        foldback_policy=foldback_policy,
        basal_policy=basal_policy,
        source_context_sequence=source_context_sequence,
    )
    prepared = prepare_context(combination)
    if isinstance(prepared, CombinationEvaluation):
        return prepared
    endpoint = (
        evaluate_pcr_endpoint(prepared)
        if prepared.pcr_bearing
        else evaluate_direct_endpoint(prepared)
    )
    if isinstance(endpoint, CombinationEvaluation):
        return endpoint
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        endpoint = evaluate_clone_endpoint(prepared, endpoint)
        if isinstance(endpoint, CombinationEvaluation):
            return endpoint
    if endpoint.reaction_report_has_errors or endpoint.end_generation_report_has_errors:
        return _materialize_evaluation(
            context=prepared,
            endpoint=endpoint,
            rejection_reason=CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT,
        )
    if request.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
        design_encoding_matches = endpoint.final_sequence == request.design.encoding_sequence
    elif request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        design_encoding_matches = endpoint.design_parent_span is not None
    else:
        design_encoding_matches = True
    if not design_encoding_matches:
        return _materialize_evaluation(
            context=prepared,
            endpoint=endpoint,
            rejection_reason=CompositionRejectionCode.DESIGN_ENCODING_MISMATCH,
        )
    return _materialize_evaluation(
        context=prepared,
        endpoint=endpoint,
        rejection_reason=None,
    )


__all__ = [
    "CombinationEvaluation",
    "CompositionRejectionCode",
    "evaluate_combination",
]
