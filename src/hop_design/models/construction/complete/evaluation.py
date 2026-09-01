"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/evaluation.py

Replays one complete-route combination against exact local and design authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.construction.payload import (
    ConstructionEndpoint,
)
from hop_design.models.enzymes import EnzymeProvisioningPolicy
from hop_design.models.reaction_replay import assess_reaction_program

from .auxiliary.evaluation import evaluate_endpoint_auxiliaries
from .clone import (
    CloneEndGenerationError,
    derive_clone_end_program_for_template,
    discover_endpoint_release,
)
from .evaluation_inputs import (
    derive_complete_payload_source_span,
    derive_endpoint_source_return_arm,
    derive_linear_source_embedding,
    derive_pcr_design_parent_span,
    derive_route_prefix,
)
from .evaluation_result import CombinationEvaluation, CompositionRejectionCode
from .pcr.products import derive_pcr_product_sequence
from .pcr.schedule import derive_pcr_reaction_program
from .pcr.validation import evaluate_pcr_compatibility
from .provisioning import merge_provisioning_policies
from .request import ConstructionDiscoveryRequest
from .route_schedule import derive_direct_reaction_program
from .source_preparation import (
    SourcePreparationResolutionError,
    resolve_route_source_preparation,
)


def evaluate_combination(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord | None,
    foldback_policy: EnzymeProvisioningPolicy,
    basal_policy: EnzymeProvisioningPolicy | None,
) -> CombinationEvaluation:
    """Evaluate one exact combination in the closed intrinsic gate order."""
    candidate_enzyme_programs = 1 + (0 if basal is None else len(basal.reaction_programs))
    recognition_placements_attempted = len(foldback.enzyme_bindings) + (
        0 if basal is None else len(basal.enzyme_bindings)
    )
    constraint_systems_attempted = 2 + (0 if basal is None else 1)
    prefix = derive_route_prefix(request, basal, foldback.payload_sequence)
    if prefix is None:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.BASAL_SOURCE_MAP_INCOMPATIBLE,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
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
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
    source, complement = tuple(
        binding.material for binding in source_preparation.produced_material_bindings
    )
    pcr_bearing = request.endpoint in {
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    }
    pcr_core = prefix + foldback.retained_sequence
    endpoint_auxiliaries = None
    if pcr_bearing:
        auxiliary_policy = request.materialization.endpoint_auxiliaries
        if basal is None or auxiliary_policy is None:
            raise ValueError("PCR-bearing composition requires basal and auxiliary policy.")
        auxiliary_evaluation = evaluate_endpoint_auxiliaries(
            policy=auxiliary_policy,
            basal=basal,
            pcr_core_sequence=pcr_core,
            source_primer_region_length_nt=len(prefix),
            prefix=prefix,
            source_return_arm=source_return_arm,
            source=source,
            source_complement=complement,
            source_preparation=source_preparation,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
        if isinstance(auxiliary_evaluation, CombinationEvaluation):
            return auxiliary_evaluation
        endpoint_auxiliaries = auxiliary_evaluation
        adapter = endpoint_auxiliaries.adapter
        forward = endpoint_auxiliaries.forward_primer
        reverse = endpoint_auxiliaries.reverse_primer
        pcr_template = pcr_core + adapter.sequence_5prime
        pcr_rejection = evaluate_pcr_compatibility(
            basal=basal,
            prefix=prefix,
            pcr_template=pcr_template,
            adapter=adapter,
            forward=forward,
            reverse=reverse,
        )
        if pcr_rejection is not None:
            return CombinationEvaluation(
                rejection_reason=pcr_rejection,
                prefix=prefix,
                source_return_arm=source_return_arm,
                source=source,
                source_complement=complement,
                source_preparation=source_preparation,
                endpoint_auxiliaries=endpoint_auxiliaries,
                candidate_enzyme_programs=candidate_enzyme_programs,
                recognition_placements_attempted=recognition_placements_attempted,
                constraint_systems_attempted=constraint_systems_attempted,
            )
    else:
        pcr_template = pcr_core + source_return_arm
    policies: tuple[EnzymeProvisioningPolicy, ...] = (foldback_policy,)
    if basal is not None:
        if basal_policy is None:
            raise ValueError("Basal composition requires its exact provisioning policy.")
        policies = (foldback_policy, basal_policy)
    program = (
        derive_pcr_reaction_program(
            foldback=foldback,
            basal=basal,
            prefix=prefix,
            source_return_arm=source_return_arm,
            source=source,
            source_complement=complement,
        )
        if pcr_bearing and basal is not None
        else derive_direct_reaction_program(
            foldback=foldback,
            basal=basal,
            prefix=prefix,
            source_return_arm=source_return_arm,
            source=source,
            source_complement=complement,
        )
    )
    merged_policy = merge_provisioning_policies(policies)
    assessment = assess_reaction_program(
        program=program,
        policy=merged_policy,
    )
    end_program = None
    end_assessment = None
    design_parent_span = None
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        release_request = request.release
        if basal is None or release_request is None:
            raise ValueError("Clone composition requires basal and endpoint-release authority.")
        assert endpoint_auxiliaries is not None
        forward = endpoint_auxiliaries.forward_primer
        reverse = endpoint_auxiliaries.reverse_primer
        pcr_product = derive_pcr_product_sequence(pcr_template, forward, reverse)
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
                prefix=prefix,
                source_return_arm=source_return_arm,
                source=source,
                source_complement=complement,
                source_preparation=source_preparation,
                endpoint_auxiliaries=endpoint_auxiliaries,
                reaction_program=program,
                stage_assessments=assessment.stage_assessments,
                pcr_template_sequence=pcr_template,
                final_sequence=request.design.encoding_sequence,
                candidate_enzyme_programs=(candidate_enzyme_programs + release.examined_site_pairs),
                recognition_placements_attempted=(
                    recognition_placements_attempted + release.examined_site_pairs * 2
                ),
                constraint_systems_attempted=constraint_systems_attempted,
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
                prefix=prefix,
                source_return_arm=source_return_arm,
                source=source,
                source_complement=complement,
                source_preparation=source_preparation,
                endpoint_auxiliaries=endpoint_auxiliaries,
                reaction_program=program,
                stage_assessments=assessment.stage_assessments,
                pcr_template_sequence=pcr_template,
                final_sequence=request.design.encoding_sequence,
                candidate_enzyme_programs=candidate_enzyme_programs,
                recognition_placements_attempted=recognition_placements_attempted,
                constraint_systems_attempted=constraint_systems_attempted,
            )
        merged_policy = merge_provisioning_policies(
            (*policies, release_request.enzyme_provisioning)
        )
        end_assessment = assess_reaction_program(program=end_program, policy=merged_policy)
        end_generation_bindings = release.bindings
    else:
        end_generation_bindings = None
    final_sequence = pcr_template
    if pcr_bearing:
        assert endpoint_auxiliaries is not None
        forward = endpoint_auxiliaries.forward_primer
        reverse = endpoint_auxiliaries.reverse_primer
        final_sequence = derive_pcr_product_sequence(pcr_template, forward, reverse)
        if request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            design_parent_span = derive_pcr_design_parent_span(
                request,
                prefix=prefix,
                top_sequence=final_sequence,
                forward_primer=forward,
            )
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        final_sequence = request.design.encoding_sequence
    if assessment.report.has_errors or (
        end_assessment is not None and end_assessment.report.has_errors
    ):
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT,
            prefix=prefix,
            source_return_arm=source_return_arm,
            source=source,
            source_complement=complement,
            source_preparation=source_preparation,
            endpoint_auxiliaries=endpoint_auxiliaries,
            reaction_program=program,
            stage_assessments=assessment.stage_assessments,
            end_generation_program=end_program,
            end_generation_stage_assessments=(
                () if end_assessment is None else end_assessment.stage_assessments
            ),
            end_generation_bindings=end_generation_bindings,
            pcr_template_sequence=pcr_template if pcr_bearing else None,
            design_parent_span=design_parent_span,
            final_sequence=final_sequence,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
    if request.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
        design_encoding_matches = final_sequence == request.design.encoding_sequence
    elif request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        design_encoding_matches = design_parent_span is not None
    else:
        design_encoding_matches = True
    if not design_encoding_matches:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.DESIGN_ENCODING_MISMATCH,
            prefix=prefix,
            source_return_arm=source_return_arm,
            source=source,
            source_complement=complement,
            source_preparation=source_preparation,
            endpoint_auxiliaries=endpoint_auxiliaries,
            reaction_program=program,
            stage_assessments=assessment.stage_assessments,
            pcr_template_sequence=pcr_template if pcr_bearing else None,
            design_parent_span=design_parent_span,
            final_sequence=final_sequence,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
    return CombinationEvaluation(
        rejection_reason=None,
        prefix=prefix,
        source_return_arm=source_return_arm,
        source=source,
        source_complement=complement,
        source_preparation=source_preparation,
        endpoint_auxiliaries=endpoint_auxiliaries,
        reaction_program=program,
        stage_assessments=assessment.stage_assessments,
        end_generation_program=end_program,
        end_generation_stage_assessments=(
            () if end_assessment is None else end_assessment.stage_assessments
        ),
        end_generation_bindings=end_generation_bindings,
        pcr_template_sequence=pcr_template if pcr_bearing else None,
        design_parent_span=design_parent_span,
        final_sequence=final_sequence,
        candidate_enzyme_programs=candidate_enzyme_programs,
        recognition_placements_attempted=recognition_placements_attempted,
        constraint_systems_attempted=constraint_systems_attempted,
    )


__all__ = [
    "CombinationEvaluation",
    "CompositionRejectionCode",
    "evaluate_combination",
]
