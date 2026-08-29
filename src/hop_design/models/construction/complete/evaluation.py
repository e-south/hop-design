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
from hop_design.models.construction.payload import SourceOrientation, _content_id
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    CharacterizedEnzymeCatalog,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    EnzymeRoleRestriction,
)
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.plan import FeatureRole
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.reactions import ReactionProgram, ReactionStageAssessment
from hop_design.models.sequence import reverse_complement_iupac

from .request import (
    ConstructionDiscoveryRequest,
    ExactConstructionMaterial,
    derived_source_material_id,
)
from .route_schedule import derive_direct_reaction_program


class CompositionRejectionCode(StrEnum):
    """Closed intrinsic and global-policy combination rejection reasons."""

    BASAL_SOURCE_MAP_INCOMPATIBLE = "basal-source-map-incompatible"
    SOURCE_END_CHEMISTRY_MISMATCH = "source-end-chemistry-mismatch"
    GLOBAL_ACTIONABLE_SITE_CONFLICT = "global-actionable-site-conflict"
    DESIGN_ENCODING_MISMATCH = "design-encoding-mismatch"
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


def _source_materials(
    request: ConstructionDiscoveryRequest,
    sequence: str,
    complement_sequence: str,
) -> tuple[ExactConstructionMaterial, ExactConstructionMaterial]:
    policy = request.materialization
    return (
        ExactConstructionMaterial(
            material_id=derived_source_material_id(sequence, complementary=False),
            origin=policy.source_origin,
            sequence_5prime=sequence,
            five_prime_end=policy.source_five_prime_end,
            three_prime_end=policy.source_three_prime_end,
        ),
        ExactConstructionMaterial(
            material_id=derived_source_material_id(complement_sequence, complementary=True),
            origin=policy.source_complement_origin,
            sequence_5prime=complement_sequence,
            five_prime_end=policy.source_complement_five_prime_end,
            three_prime_end=policy.source_complement_three_prime_end,
        ),
    )


def _catalog_entries(
    policies: tuple[EnzymeProvisioningPolicy, ...],
) -> tuple[CharacterizedEnzyme, ...]:
    entries: dict[str, CharacterizedEnzyme] = {}
    for policy in policies:
        for enzyme in policy.catalog.enzymes:
            previous = entries.setdefault(enzyme.enzyme_id, enzyme)
            if previous != enzyme:
                raise ValueError("Complete route cannot merge conflicting enzyme definitions.")
    return tuple(entries[key] for key in sorted(entries))


def merge_provisioning_policies(
    policies: tuple[EnzymeProvisioningPolicy, ...],
) -> EnzymeProvisioningPolicy:
    """Merge exact local policies without weakening restrictions or limits."""
    enzymes = _catalog_entries(policies)
    restrictions: dict[EnzymeRole, EnzymeRoleRestriction] = {}
    for policy in policies:
        for restriction in policy.role_restrictions:
            previous = restrictions.setdefault(restriction.role, restriction)
            if previous != restriction:
                raise ValueError("Complete route cannot merge conflicting role restrictions.")
    limits = tuple(policy.max_operations for policy in policies)
    return EnzymeProvisioningPolicy(
        catalog=CharacterizedEnzymeCatalog(
            catalog_id=_content_id(
                "enzyme-catalog",
                1,
                tuple(item.model_dump(mode="json") for item in enzymes),
            ),
            enzymes=enzymes,
        ),
        allowed_enzyme_ids=tuple(
            sorted(
                {
                    enzyme_id
                    for policy in policies
                    for enzyme_id in (
                        policy.allowed_enzyme_ids
                        or tuple(item.enzyme_id for item in policy.catalog.enzymes)
                    )
                }
            )
        ),
        forbidden_enzyme_ids=tuple(
            sorted({item for policy in policies for item in policy.forbidden_enzyme_ids})
        ),
        reserved_enzyme_ids=tuple(
            sorted({item for policy in policies for item in policy.reserved_enzyme_ids})
        ),
        max_operations=(
            None
            if any(item is None for item in limits)
            else sum(item for item in limits if item is not None)
        ),
        role_restrictions=tuple(restrictions[key] for key in sorted(restrictions)),
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
    prefix = _prefix(request, basal, foldback.payload_sequence)
    if prefix is None:
        return CombinationEvaluation(
            rejection_reason=CompositionRejectionCode.BASAL_SOURCE_MAP_INCOMPATIBLE,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )
    _, return_arm, _ = _design_context(request)
    source, complement = _source_materials(
        request,
        prefix + foldback.source_reference_sequence,
        reverse_complement_iupac(foldback.source_reference_sequence) + return_arm,
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
    program = derive_direct_reaction_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        return_arm=return_arm,
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
    "merge_provisioning_policies",
]
