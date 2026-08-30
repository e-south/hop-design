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
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.sequence import reverse_complement_iupac

from .clone import CloneEndGenerationError, derive_clone_end_program_for_template
from .evaluation_inputs import derive_route_prefix, derive_route_return_arm
from .evaluation_result import CombinationEvaluation, CompositionRejectionCode
from .materials import derive_source_materials
from .provisioning import merge_provisioning_policies
from .request import ConstructionDiscoveryRequest
from .route_schedule import derive_direct_reaction_program, derive_pcr_reaction_program


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
    source, complement = derive_source_materials(
        request,
        prefix + foldback.source_reference_sequence,
        reverse_complement_iupac(foldback.source_reference_sequence) + return_arm,
    )
    pcr_bearing = request.endpoint in {
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    }
    pcr_template = prefix + foldback.retained_sequence + return_arm
    if pcr_bearing:
        if (
            basal is None
            or basal.basal_nick.strand is not Strand.BOTTOM
            or basal.basal_nick.boundary.offset != len(prefix)
        ):
            return CombinationEvaluation(
                rejection_reason=CompositionRejectionCode.PCR_BASAL_OPEN_INCOMPATIBLE,
                prefix=prefix,
                return_arm=return_arm,
                source=source,
                source_complement=complement,
                candidate_enzyme_programs=candidate_enzyme_programs,
                recognition_placements_attempted=recognition_placements_attempted,
                constraint_systems_attempted=constraint_systems_attempted,
            )
        adapter = request.materialization.adapter
        local_adapter = next(
            (item for item in basal.materials if item.material_id == "ligation-adapter"),
            None,
        )
        if (
            adapter is None
            or local_adapter is None
            or adapter.sequence_5prime != return_arm
            or local_adapter.sequence_5prime != return_arm
            or adapter.five_prime_end is not EndChemistry.PHOSPHATE
            or adapter.three_prime_end is not EndChemistry.HYDROXYL
        ):
            return CombinationEvaluation(
                rejection_reason=CompositionRejectionCode.PCR_ADAPTER_MISMATCH,
                prefix=prefix,
                return_arm=return_arm,
                source=source,
                source_complement=complement,
                candidate_enzyme_programs=candidate_enzyme_programs,
                recognition_placements_attempted=recognition_placements_attempted,
                constraint_systems_attempted=constraint_systems_attempted,
            )
        profile = basal.projection.pairing_profile
        complex_state = basal.adapter_annealed_complex
        if (
            profile is None
            or complex_state is None
            or profile.adapter_span.end.offset > len(return_arm)
            or tuple(
                (
                    pair.left_index - profile.source_span.start.offset,
                    pair.right_index,
                    pair.left_base,
                    pair.right_base,
                )
                for pair in complex_state.pairs
            )
            != tuple(
                (
                    pair.source_index,
                    pair.adapter_index,
                    pair.source_base,
                    pair.adapter_base,
                )
                for pair in profile.pairs
            )
        ):
            return CombinationEvaluation(
                rejection_reason=CompositionRejectionCode.PCR_PAIRING_PROFILE_MISMATCH,
                prefix=prefix,
                return_arm=return_arm,
                source=source,
                source_complement=complement,
                candidate_enzyme_programs=candidate_enzyme_programs,
                recognition_placements_attempted=recognition_placements_attempted,
                constraint_systems_attempted=constraint_systems_attempted,
            )
        forward = request.materialization.forward_primer
        reverse = request.materialization.reverse_primer
        if (
            forward is None
            or reverse is None
            or forward.three_prime_end is not EndChemistry.HYDROXYL
            or reverse.three_prime_end is not EndChemistry.HYDROXYL
            or forward.sequence_5prime != pcr_template[: len(forward.sequence_5prime)]
            or reverse.sequence_5prime
            != reverse_complement_iupac(pcr_template[-len(reverse.sequence_5prime) :])
        ):
            return CombinationEvaluation(
                rejection_reason=CompositionRejectionCode.PCR_PRIMER_MISMATCH,
                prefix=prefix,
                return_arm=return_arm,
                source=source,
                source_complement=complement,
                candidate_enzyme_programs=candidate_enzyme_programs,
                recognition_placements_attempted=recognition_placements_attempted,
                constraint_systems_attempted=constraint_systems_attempted,
            )
    if (
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
        )
        if pcr_bearing and basal is not None
        else derive_direct_reaction_program(
            foldback=foldback,
            basal=basal,
            prefix=prefix,
            return_arm=return_arm,
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
        if basal is None:
            raise ValueError("Clone composition requires one exact basal authority.")
        try:
            end_program, design_parent_span = derive_clone_end_program_for_template(
                basal=basal,
                foldback=foldback,
                pcr_top=pcr_template,
                design_sequence=request.design.encoding_sequence,
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
        end_assessment = assess_reaction_program(program=end_program, policy=merged_policy)
    final_sequence = (
        request.design.encoding_sequence
        if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX
        else pcr_template
    )
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
