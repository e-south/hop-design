"""Evaluate the basal-open ligation route without downstream primer or release gates."""

from hop_design.models.junction import Strand
from hop_design.models.reaction_replay import assess_reaction_program

from ..auxiliary.resolution import EndpointAuxiliaryResolutionError, resolve_adapter
from ..evaluation_inputs import derive_joined_design_parent_span
from ..pcr.source import derive_pcr_source
from ..source_partition.errors import (
    COMPOSITION_REJECTION_BY_BINDING_FAILURE,
    SourcePartitionBindingError,
)
from .context import PreparedContext, merged_provisioning_policy
from .result import CombinationEvaluation, CompositionRejectionCode, EndpointEvaluation


def evaluate_adapter_endpoint(
    context: PreparedContext,
) -> EndpointEvaluation | CombinationEvaluation:
    combination = context.combination
    basal = combination.basal
    request = combination.request
    policy = request.materialization.adapter_ligation
    if basal is None or policy is None:
        raise ValueError("Adapter ligation requires basal authority and adapter policy.")
    if basal.basal_nick.strand is not Strand.BOTTOM:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.PCR_BASAL_OPEN_INCOMPATIBLE,
            candidate_enzyme_programs=combination.candidate_enzyme_programs,
            recognition_placements_attempted=combination.recognition_placements_attempted,
            constraint_systems_attempted=combination.constraint_systems_attempted,
        )
    try:
        adapter = resolve_adapter(policy, basal=basal, source_prefix=context.prefix)
        reaction = derive_pcr_source(
            foldback=combination.foldback,
            basal=basal,
            preparation=context.source_preparation,
            partition=combination.source_partition_plan,
        ).reaction
    except EndpointAuxiliaryResolutionError as error:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.PCR_ADAPTER_MISMATCH,
            preparation_constraint=error.diagnostic,
            candidate_enzyme_programs=combination.candidate_enzyme_programs,
            recognition_placements_attempted=combination.recognition_placements_attempted,
            constraint_systems_attempted=combination.constraint_systems_attempted,
        )
    except SourcePartitionBindingError as error:
        return CombinationEvaluation(
            rejection_reason=COMPOSITION_REJECTION_BY_BINDING_FAILURE[error.code],
            candidate_enzyme_programs=combination.candidate_enzyme_programs,
            recognition_placements_attempted=combination.recognition_placements_attempted,
            constraint_systems_attempted=combination.constraint_systems_attempted,
        )
    assessment = assess_reaction_program(
        program=reaction, policy=merged_provisioning_policy(context)
    )
    sequence = context.pcr_core_sequence + adapter.sequence_5prime
    return EndpointEvaluation(
        endpoint_auxiliaries=None,
        adapter=adapter,
        reaction_program=reaction,
        stage_assessments=assessment.stage_assessments,
        reaction_report_has_errors=assessment.report.has_errors,
        pcr_template_sequence=None,
        final_sequence=sequence,
        design_parent_span=derive_joined_design_parent_span(
            request, prefix=context.prefix, sequence=sequence
        ),
    )
