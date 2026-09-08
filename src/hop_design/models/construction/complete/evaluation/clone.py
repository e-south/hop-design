"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/evaluation/clone.py

Evaluates clone-ready endpoint release and end-generation requirements.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import replace

from hop_design.models.enzymes import EnzymeRole
from hop_design.models.reaction_replay import assess_reaction_program

from ..clone import (
    CloneEndGenerationError,
    derive_clone_end_program_for_template,
    discover_endpoint_release,
)
from ..pcr.products import derive_pcr_product_sequence
from ..provisioning import merge_provisioning_policies
from .context import PreparedContext, provisioning_policies
from .result import CombinationEvaluation, CompositionRejectionCode, EndpointEvaluation


def evaluate_clone_endpoint(
    context: PreparedContext,
    endpoint: EndpointEvaluation,
) -> EndpointEvaluation | CombinationEvaluation:
    """Run clone-release discovery and exact end-generation gates."""
    combination = context.combination
    request = combination.request
    basal = combination.basal
    release_request = request.release
    if basal is None or release_request is None:
        raise ValueError("Clone composition requires basal and endpoint-release authority.")
    local_release = basal.future_release_action
    release_enzyme_ids = tuple(
        enzyme.enzyme_id
        for enzyme in release_request.enzyme_provisioning.catalog.enzymes
        if release_request.enzyme_provisioning.permits(
            enzyme.enzyme_id,
            role=EnzymeRole.END_GENERATION,
        )
    )
    local_requirement = None if local_release is None else local_release.requirement
    required = (
        release_request.left
        if local_requirement is not None and local_requirement.product_end == "left"
        else release_request.right
    )
    if (
        local_release is None
        or local_requirement is None
        or release_enzyme_ids != (local_release.enzyme_id,)
        or local_requirement.orientation is not required.orientation
        or local_requirement.overhang_end is not required.overhang_end
        or local_requirement.cohesive_end_sequence != required.cohesive_end_sequence
    ):
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.CLONE_LOCAL_RELEASE_INCOMPATIBLE,
            prefix=context.prefix,
            source_return_arm=context.source_return_arm,
            source=context.source,
            source_complement=context.source_complement,
            source_preparation=context.source_preparation,
            endpoint_auxiliaries=endpoint.endpoint_auxiliaries,
            reaction_program=endpoint.reaction_program,
            stage_assessments=endpoint.stage_assessments,
            pcr_template_sequence=endpoint.pcr_template_sequence,
            final_sequence=request.design.encoding_sequence,
            candidate_enzyme_programs=combination.candidate_enzyme_programs,
            recognition_placements_attempted=combination.recognition_placements_attempted,
            constraint_systems_attempted=combination.constraint_systems_attempted,
        )
    auxiliaries = endpoint.endpoint_auxiliaries
    if auxiliaries is None or endpoint.pcr_template_sequence is None:
        raise ValueError("Clone composition requires resolved PCR endpoint auxiliaries.")
    pcr_product = derive_pcr_product_sequence(
        endpoint.pcr_template_sequence,
        auxiliaries.forward_primer,
        auxiliaries.reverse_primer,
    )
    release = discover_endpoint_release(
        request=release_request,
        pcr_top=pcr_product,
        design_sequence=request.design.encoding_sequence,
    )
    if release.bindings is None:
        return CombinationEvaluation(
            rejection_reason=(
                None
                if release.truncated
                else CompositionRejectionCode.CLONE_END_GENERATION_AMBIGUOUS
                if release.ambiguous
                else CompositionRejectionCode.CLONE_END_GENERATION_INCOMPATIBLE
            ),
            truncation_reason=("endpoint:max_site_pairs" if release.truncated else None),
            prefix=context.prefix,
            source_return_arm=context.source_return_arm,
            source=context.source,
            source_complement=context.source_complement,
            source_preparation=context.source_preparation,
            endpoint_auxiliaries=auxiliaries,
            reaction_program=endpoint.reaction_program,
            stage_assessments=endpoint.stage_assessments,
            pcr_template_sequence=endpoint.pcr_template_sequence,
            final_sequence=request.design.encoding_sequence,
            candidate_enzyme_programs=(
                combination.candidate_enzyme_programs + release.examined_site_pairs
            ),
            recognition_placements_attempted=(
                combination.recognition_placements_attempted + release.examined_site_pairs * 2
            ),
            constraint_systems_attempted=combination.constraint_systems_attempted,
        )
    try:
        end_program, design_parent_span = derive_clone_end_program_for_template(
            pcr_top=pcr_product,
            design_sequence=request.design.encoding_sequence,
            bindings=release.bindings,
        )
    except CloneEndGenerationError:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.CLONE_END_GENERATION_INCOMPATIBLE,
            prefix=context.prefix,
            source_return_arm=context.source_return_arm,
            source=context.source,
            source_complement=context.source_complement,
            source_preparation=context.source_preparation,
            endpoint_auxiliaries=auxiliaries,
            reaction_program=endpoint.reaction_program,
            stage_assessments=endpoint.stage_assessments,
            pcr_template_sequence=endpoint.pcr_template_sequence,
            final_sequence=request.design.encoding_sequence,
            candidate_enzyme_programs=combination.candidate_enzyme_programs,
            recognition_placements_attempted=combination.recognition_placements_attempted,
            constraint_systems_attempted=combination.constraint_systems_attempted,
        )
    merged_policy = merge_provisioning_policies(
        (*provisioning_policies(context), release_request.enzyme_provisioning)
    )
    end_assessment = assess_reaction_program(program=end_program, policy=merged_policy)
    return replace(
        endpoint,
        end_generation_program=end_program,
        end_generation_stage_assessments=end_assessment.stage_assessments,
        end_generation_report_has_errors=end_assessment.report.has_errors,
        end_generation_bindings=release.bindings,
        design_parent_span=design_parent_span,
        final_sequence=request.design.encoding_sequence,
    )
