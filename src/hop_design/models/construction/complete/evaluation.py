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
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackMaterialRequirement,
)
from hop_design.models.construction.payload import (
    ConstructionEndpoint,
)
from hop_design.models.enzymes import EnzymeProvisioningPolicy
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.sequence import reverse_complement_iupac

from .clone import (
    CloneEndGenerationError,
    derive_clone_end_program_for_template,
    discover_endpoint_release,
)
from .evaluation_inputs import (
    derive_linear_source_embedding,
    derive_route_prefix,
    derive_route_return_arm,
)
from .evaluation_result import CombinationEvaluation, CompositionRejectionCode
from .materials import derive_source_materials
from .pcr.schedule import derive_pcr_reaction_program
from .pcr.validation import evaluate_pcr_compatibility
from .provisioning import merge_provisioning_policies
from .request import ConstructionDiscoveryRequest
from .route_schedule import derive_direct_reaction_program


def _reverse_handle_sequence(request: ConstructionDiscoveryRequest) -> str:
    reverse = request.materialization.reverse_primer
    if reverse is None or not reverse.five_prime_handle:
        return ""
    return reverse_complement_iupac(reverse.five_prime_handle)


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
    return_arm = derive_route_return_arm(request, basal)
    if return_arm is None:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.CLONE_END_GENERATION_INCOMPATIBLE,
            prefix=prefix,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
    embedding = derive_linear_source_embedding(
        foldback=foldback,
        prefix=prefix,
        return_arm=return_arm,
    )
    source, complement = derive_source_materials(
        request,
        embedding.source_sequence,
        embedding.complement_sequence,
    )
    pcr_bearing = request.endpoint in {
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    }
    pcr_template = prefix + foldback.retained_sequence + return_arm
    if pcr_bearing:
        pcr_rejection = evaluate_pcr_compatibility(
            request,
            basal=basal,
            prefix=prefix,
            return_arm=return_arm,
            pcr_template=pcr_template,
        )
        if pcr_rejection is not None:
            return CombinationEvaluation(
                rejection_reason=pcr_rejection,
                prefix=prefix,
                return_arm=return_arm,
                source=source,
                source_complement=complement,
                candidate_enzyme_programs=candidate_enzyme_programs,
                recognition_placements_attempted=recognition_placements_attempted,
                constraint_systems_attempted=constraint_systems_attempted,
            )
    if (
        FoldbackMaterialRequirement.SOURCE_TOP_5PRIME_PHOSPHATE in foldback.material_requirements
        and source.five_prime_end is not EndChemistry.PHOSPHATE
    ) or (
        FoldbackMaterialRequirement.SOURCE_BOTTOM_5PRIME_PHOSPHATE in foldback.material_requirements
        and complement.five_prime_end is not EndChemistry.PHOSPHATE
    ):
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.SOURCE_END_CHEMISTRY_MISMATCH,
            prefix=prefix,
            return_arm=return_arm,
            source=source,
            source_complement=complement,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
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
            return_arm=return_arm,
            source=source,
            source_complement=complement,
        )
        if pcr_bearing and basal is not None
        else derive_direct_reaction_program(
            foldback=foldback,
            basal=basal,
            prefix=prefix,
            return_arm=return_arm,
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
        forward = request.materialization.forward_primer
        reverse = request.materialization.reverse_primer
        assert forward is not None and reverse is not None
        pcr_product = forward.five_prime_handle + pcr_template + _reverse_handle_sequence(request)
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
                return_arm=return_arm,
                source=source,
                source_complement=complement,
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
                return_arm=return_arm,
                source=source,
                source_complement=complement,
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
        forward = request.materialization.forward_primer
        reverse = request.materialization.reverse_primer
        assert forward is not None and reverse is not None
        final_sequence = (
            forward.five_prime_handle + pcr_template + _reverse_handle_sequence(request)
        )
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        final_sequence = request.design.encoding_sequence
    if assessment.report.has_errors or (
        end_assessment is not None and end_assessment.report.has_errors
    ):
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT,
            prefix=prefix,
            return_arm=return_arm,
            source=source,
            source_complement=complement,
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
    if (
        request.endpoint is not ConstructionEndpoint.CLONE_READY_DUPLEX
        and final_sequence != request.design.encoding_sequence
    ):
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.DESIGN_ENCODING_MISMATCH,
            prefix=prefix,
            return_arm=return_arm,
            source=source,
            source_complement=complement,
            reaction_program=program,
            stage_assessments=assessment.stage_assessments,
            pcr_template_sequence=pcr_template if pcr_bearing else None,
            final_sequence=final_sequence,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
    return CombinationEvaluation(
        rejection_reason=None,
        prefix=prefix,
        return_arm=return_arm,
        source=source,
        source_complement=complement,
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
