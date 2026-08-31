"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/auxiliary/evaluation.py

Maps endpoint auxiliary resolution into exact combination-evaluation outcomes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord

from ..evaluation_result import CombinationEvaluation, CompositionRejectionCode
from ..material import ExactConstructionMaterial
from ..source_preparation import SourceDuplexPreparationAuthority
from .policy import EndpointAuxiliaryPolicy
from .resolution import (
    EndpointAuxiliaryResolution,
    EndpointAuxiliaryResolutionError,
    EndpointAuxiliaryResolutionFailure,
    resolve_endpoint_auxiliaries,
)


def evaluate_endpoint_auxiliaries(
    *,
    policy: EndpointAuxiliaryPolicy,
    basal: BasalRealizationRecord,
    pcr_core_sequence: str,
    source_primer_region_length_nt: int,
    prefix: str,
    source_return_arm: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
    source_preparation: SourceDuplexPreparationAuthority,
    candidate_enzyme_programs: int,
    recognition_placements_attempted: int,
    constraint_systems_attempted: int,
) -> EndpointAuxiliaryResolution | CombinationEvaluation:
    """Resolve exact endpoint materials or return one closed rejection outcome."""
    try:
        return resolve_endpoint_auxiliaries(
            policy=policy,
            basal=basal,
            pcr_core_sequence=pcr_core_sequence,
            source_primer_region_length_nt=source_primer_region_length_nt,
        )
    except EndpointAuxiliaryResolutionError as exc:
        return CombinationEvaluation(
            rejection_reason=(
                CompositionRejectionCode.PCR_ADAPTER_MISMATCH
                if exc.failure is EndpointAuxiliaryResolutionFailure.ADAPTER
                else CompositionRejectionCode.PCR_PRIMER_MISMATCH
            ),
            prefix=prefix,
            source_return_arm=source_return_arm,
            source=source,
            source_complement=source_complement,
            source_preparation=source_preparation,
            candidate_enzyme_programs=candidate_enzyme_programs,
            recognition_placements_attempted=recognition_placements_attempted,
            constraint_systems_attempted=constraint_systems_attempted,
        )


__all__ = ["evaluate_endpoint_auxiliaries"]
