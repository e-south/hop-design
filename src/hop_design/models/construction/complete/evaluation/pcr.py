"""PCR-bearing endpoint preparation and compatibility evaluation."""

from __future__ import annotations

from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.reaction_replay import assess_reaction_program

from ..auxiliary.evaluation import evaluate_endpoint_auxiliaries
from ..evaluation_inputs import derive_pcr_design_parent_span
from ..pcr.products import derive_pcr_product_sequence
from ..pcr.source import derive_pcr_source
from ..pcr.validation import evaluate_pcr_compatibility
from ..source_partition.errors import (
    COMPOSITION_REJECTION_BY_BINDING_FAILURE,
    SourcePartitionBindingError,
)
from .context import PreparedContext, merged_provisioning_policy
from .result import CombinationEvaluation, EndpointEvaluation


def evaluate_pcr_endpoint(
    context: PreparedContext,
) -> EndpointEvaluation | CombinationEvaluation:
    """Run auxiliary, PCR-compatibility, and primary-program gates in order."""
    combination = context.combination
    request = combination.request
    basal = combination.basal
    auxiliary_policy = request.materialization.endpoint_auxiliaries
    if basal is None or auxiliary_policy is None:
        raise ValueError("PCR-bearing composition requires basal and auxiliary policy.")
    auxiliary_evaluation = evaluate_endpoint_auxiliaries(
        policy=auxiliary_policy,
        basal=basal,
        pcr_core_sequence=context.pcr_core_sequence,
        source_primer_region_length_nt=len(context.prefix),
        prefix=context.prefix,
        source_return_arm=context.source_return_arm,
        source=context.source,
        source_complement=context.source_complement,
        source_preparation=context.source_preparation,
        candidate_enzyme_programs=combination.candidate_enzyme_programs,
        recognition_placements_attempted=combination.recognition_placements_attempted,
        constraint_systems_attempted=combination.constraint_systems_attempted,
    )
    if isinstance(auxiliary_evaluation, CombinationEvaluation):
        return auxiliary_evaluation
    adapter = auxiliary_evaluation.adapter
    forward = auxiliary_evaluation.forward_primer
    reverse = auxiliary_evaluation.reverse_primer
    pcr_template = context.pcr_core_sequence + adapter.sequence_5prime
    pcr_rejection = evaluate_pcr_compatibility(
        basal=basal,
        prefix=context.prefix,
        pcr_template=pcr_template,
        adapter=adapter,
        forward=forward,
        reverse=reverse,
    )
    if pcr_rejection is not None:
        return CombinationEvaluation(
            rejection_reason=pcr_rejection,
            prefix=context.prefix,
            source_return_arm=context.source_return_arm,
            source=context.source,
            source_complement=context.source_complement,
            source_preparation=context.source_preparation,
            endpoint_auxiliaries=auxiliary_evaluation,
            candidate_enzyme_programs=combination.candidate_enzyme_programs,
            recognition_placements_attempted=combination.recognition_placements_attempted,
            constraint_systems_attempted=combination.constraint_systems_attempted,
        )
    try:
        program = derive_pcr_source(
            foldback=combination.foldback,
            basal=basal,
            preparation=context.source_preparation,
            partition=combination.source_partition_plan,
        ).reaction
    except SourcePartitionBindingError as exc:
        return CombinationEvaluation(
            rejection_reason=COMPOSITION_REJECTION_BY_BINDING_FAILURE[exc.code],
            candidate_enzyme_programs=combination.candidate_enzyme_programs,
            recognition_placements_attempted=combination.recognition_placements_attempted,
            constraint_systems_attempted=combination.constraint_systems_attempted,
        )
    assessment = assess_reaction_program(
        program=program,
        policy=merged_provisioning_policy(context),
    )
    final_sequence = derive_pcr_product_sequence(pcr_template, forward, reverse)
    design_parent_span = None
    if request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        design_parent_span = derive_pcr_design_parent_span(
            request,
            prefix=context.prefix,
            top_sequence=final_sequence,
            forward_primer=forward,
        )
    return EndpointEvaluation(
        endpoint_auxiliaries=auxiliary_evaluation,
        reaction_program=program,
        stage_assessments=assessment.stage_assessments,
        reaction_report_has_errors=assessment.report.has_errors,
        pcr_template_sequence=pcr_template,
        design_parent_span=design_parent_span,
        final_sequence=final_sequence,
    )
