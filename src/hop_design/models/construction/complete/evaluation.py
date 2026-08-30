"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/evaluation.py

Replays one complete-route combination against exact local and design authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackMaterialRequirement,
)
from hop_design.models.construction.payload import (
    ConstructionEndpoint,
    SourceOrientation,
)
from hop_design.models.enzymes import EnzymeProvisioningPolicy
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.plan import FeatureRole
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.reactions import ReactionProgram, ReactionStageAssessment
from hop_design.models.sequence import reverse_complement_iupac

from .materials import derive_source_materials
from .provisioning import merge_provisioning_policies
from .request import (
    ConstructionDiscoveryRequest,
    ExactConstructionMaterial,
)
from .route_schedule import derive_direct_reaction_program, derive_pcr_reaction_program


class CompositionRejectionCode(StrEnum):
    """Closed intrinsic and global-policy combination rejection reasons."""

    BASAL_SOURCE_MAP_INCOMPATIBLE = "basal-source-map-incompatible"
    SOURCE_END_CHEMISTRY_MISMATCH = "source-end-chemistry-mismatch"
    GLOBAL_ACTIONABLE_SITE_CONFLICT = "global-actionable-site-conflict"
    DESIGN_ENCODING_MISMATCH = "design-encoding-mismatch"
    PCR_BASAL_OPEN_INCOMPATIBLE = "pcr-basal-open-incompatible"
    PCR_ADAPTER_MISMATCH = "pcr-adapter-mismatch"
    PCR_PAIRING_PROFILE_MISMATCH = "pcr-pairing-profile-mismatch"
    PCR_PRIMER_MISMATCH = "pcr-primer-mismatch"
    ALL_COMBINATIONS_VALID_REQUIRED = "all-combinations-valid-required"


@dataclass(frozen=True, slots=True)
class CombinationEvaluation:
    """Deterministic evaluation facts shared by generation and result replay."""

    rejection_reason: CompositionRejectionCode | None
    candidate_enzyme_programs: int
    recognition_placements_attempted: int
    constraint_systems_attempted: int
    prefix: str | None = None
    return_arm: str | None = None
    source: ExactConstructionMaterial | None = None
    source_complement: ExactConstructionMaterial | None = None
    reaction_program: ReactionProgram | None = None
    stage_assessments: tuple[ReactionStageAssessment, ...] = ()
    final_sequence: str | None = None


def _design_context(request: ConstructionDiscoveryRequest) -> tuple[str, str, str]:
    features = request.design.plan.hairpin_encoding_insert.features
    payload_index = next(
        (index for index, feature in enumerate(features) if feature.role is FeatureRole.PAYLOAD),
        None,
    )
    paired_index = next(
        (
            index
            for index, feature in enumerate(features)
            if feature.role is FeatureRole.PAIRED_PAYLOAD
        ),
        None,
    )
    if payload_index is None or paired_index is None:
        raise ValueError("Complete route requires exact payload feature boundaries.")
    left = "".join(feature.sequence for feature in features[:payload_index])
    right = "".join(feature.sequence for feature in features[paired_index + 1 :])
    basal_left = tuple(
        feature.sequence for feature in features if feature.role is FeatureRole.BASAL_LEFT_ARM
    )
    if len(basal_left) != 1 or len(left) != len(right):
        raise ValueError("Complete route requires length-matched exact peripheral arms.")
    return left, right, basal_left[0]


def _prefix(
    request: ConstructionDiscoveryRequest,
    basal: BasalRealizationRecord | None,
    payload: str,
) -> str | None:
    design_prefix, _, basal_left = _design_context(request)
    if basal is None:
        return design_prefix
    if len(basal.payload_source_map.segments) != 1:
        return None
    segment = basal.payload_source_map.segments[0]
    start = segment.source_span.start.offset
    end = segment.source_span.end.offset
    if (
        segment.orientation is not SourceOrientation.FORWARD
        or end != len(basal.source_precursor_sequence)
        or basal.source_precursor_sequence[start:end] != payload
    ):
        return None
    prefix = basal.source_precursor_sequence[:start]
    return design_prefix if prefix == basal_left else None


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
    prefix = _prefix(request, basal, foldback.payload_sequence)
    if prefix is None:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.BASAL_SOURCE_MAP_INCOMPATIBLE,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
    _, return_arm, _ = _design_context(request)
    source, complement = derive_source_materials(
        request,
        prefix + foldback.source_reference_sequence,
        reverse_complement_iupac(foldback.source_reference_sequence) + return_arm,
    )
    if request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
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
            or len(profile.pairs) != len(return_arm)
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
        encoding = request.design.encoding_sequence
        if (
            forward is None
            or reverse is None
            or forward.three_prime_end is not EndChemistry.HYDROXYL
            or reverse.three_prime_end is not EndChemistry.HYDROXYL
            or forward.sequence_5prime != encoding[: len(forward.sequence_5prime)]
            or reverse.sequence_5prime
            != reverse_complement_iupac(encoding[-len(reverse.sequence_5prime) :])
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
        if request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX and basal is not None
        else derive_direct_reaction_program(
            foldback=foldback,
            basal=basal,
            prefix=prefix,
            return_arm=return_arm,
        )
    )
    assessment = assess_reaction_program(
        program=program,
        policy=merge_provisioning_policies(policies),
    )
    final_sequence = prefix + foldback.retained_sequence + return_arm
    if assessment.report.has_errors:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT,
            prefix=prefix,
            return_arm=return_arm,
            source=source,
            source_complement=complement,
            reaction_program=program,
            stage_assessments=assessment.stage_assessments,
            final_sequence=final_sequence,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
    if final_sequence != request.design.encoding_sequence:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.DESIGN_ENCODING_MISMATCH,
            prefix=prefix,
            return_arm=return_arm,
            source=source,
            source_complement=complement,
            reaction_program=program,
            stage_assessments=assessment.stage_assessments,
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
