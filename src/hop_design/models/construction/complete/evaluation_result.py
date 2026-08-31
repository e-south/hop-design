"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/evaluation_result.py

Defines closed outcomes and derived facts for one complete-route evaluation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hop_design.models.construction.enzyme_binding import ConstructionEnzymeBinding
from hop_design.models.coordinates import Span
from hop_design.models.reactions import ReactionProgram, ReactionStageAssessment

from .request import ExactConstructionMaterial


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
    CLONE_END_GENERATION_INCOMPATIBLE = "clone-end-generation-incompatible"
    CLONE_END_GENERATION_AMBIGUOUS = "clone-end-generation-ambiguous"
    ALL_COMBINATIONS_VALID_REQUIRED = "all-combinations-valid-required"


@dataclass(frozen=True, slots=True)
class CombinationEvaluation:
    """Deterministic evaluation facts shared by generation and result replay."""

    rejection_reason: CompositionRejectionCode | None
    candidate_enzyme_programs: int
    recognition_placements_attempted: int
    constraint_systems_attempted: int
    truncation_reason: str | None = None
    prefix: str | None = None
    source_return_arm: str | None = None
    source: ExactConstructionMaterial | None = None
    source_complement: ExactConstructionMaterial | None = None
    reaction_program: ReactionProgram | None = None
    stage_assessments: tuple[ReactionStageAssessment, ...] = ()
    end_generation_program: ReactionProgram | None = None
    end_generation_stage_assessments: tuple[ReactionStageAssessment, ...] = ()
    end_generation_bindings: tuple[ConstructionEnzymeBinding, ConstructionEnzymeBinding] | None = (
        None
    )
    pcr_template_sequence: str | None = None
    design_parent_span: Span | None = None
    final_sequence: str | None = None


__all__ = ["CombinationEvaluation", "CompositionRejectionCode"]
