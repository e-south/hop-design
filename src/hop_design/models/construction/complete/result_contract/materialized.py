"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/result_contract/materialized.py

Validates materialized routes against requests and deterministic evaluations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any

from hop_design.models.construction.payload import ConstructionEndpoint

from ..authority import CompositionDisposition, ConstructionCompositionProvenance
from ..evaluation_result import CombinationEvaluation
from ..payload_validation import validate_payload_source_map
from ..request import ConstructionDiscoveryRequest
from ..state import ConstructionStatePhase


def validate_endpoint_evidence(
    request: ConstructionDiscoveryRequest,
    realization: Any,
) -> None:
    """Require final topology and terminal phase to match the requested endpoint."""
    if realization.final_product.reference.endpoint is not request.endpoint:
        raise ValueError("Final product endpoint must match the exact request.")
    topology = realization.final_product.reference.topology
    terminal_phase = realization.construction_program.states[-1].phase
    if request.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN and (
        topology != "single_stranded_hairpin"
        or terminal_phase is not ConstructionStatePhase.LIGATED_PRODUCT
    ):
        raise ValueError("Direct final product topology and terminal phase must match.")
    if request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX and (
        topology != "linear_duplex"
        or terminal_phase is not ConstructionStatePhase.HAIRPIN_PCR_DUPLEX
    ):
        raise ValueError("PCR final product topology and terminal phase must match.")
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX and (
        topology != "linear_duplex"
        or terminal_phase is not ConstructionStatePhase.CLONE_READY_DUPLEX
        or tuple(end.product_end for end in realization.final_product.cohesive_ends)
        != ("left", "right")
    ):
        raise ValueError("Clone-ready topology, terminal phase, and cohesive ends must match.")


def validate_materialized_request(
    *,
    request: ConstructionDiscoveryRequest,
    provenance: ConstructionCompositionProvenance,
    disposition: CompositionDisposition,
    realization: Any,
) -> None:
    """Cross-bind one materialized route to its request and upstream domains."""
    if realization.design != request.design:
        raise ValueError("Materialized design authority must equal the exact result request.")
    validate_payload_source_map(request, realization)
    source, source_complement, *auxiliaries = realization.materials
    policy = request.materialization
    expected_auxiliaries = tuple(
        item
        for item in (
            policy.adapter,
            (
                None
                if policy.hairpin_pcr_forward_primer is None
                else policy.hairpin_pcr_forward_primer.oligo
            ),
            (
                None
                if policy.hairpin_pcr_reverse_primer is None
                else policy.hairpin_pcr_reverse_primer.oligo
            ),
        )
        if item is not None
    )
    if (
        source.sequence_5prime != realization.realization.precursor_sequence
        or tuple(
            binding.material
            for binding in realization.source_preparation.produced_material_bindings
        )
        != (source, source_complement)
        or tuple(auxiliaries) != expected_auxiliaries
    ):
        raise ValueError("Materialized set must equal the exact result request policy.")
    if (
        realization.foldback_realization_id != disposition.foldback_realization_id
        or realization.basal_realization_id != disposition.basal_realization_id
    ):
        raise ValueError("Materialized local authorities must equal their exact disposition.")
    if realization.foldback_realization_id not in provenance.foldback_realization_ids:
        raise ValueError("Materialized route must bind one verified foldback authority.")
    if realization.basal_realization_id is not None and (
        realization.basal_realization_id not in provenance.basal_realization_ids
    ):
        raise ValueError("Materialized route must bind one verified basal authority.")
    expected_local_ids = (
        *((realization.basal_realization_id,) if realization.basal_realization_id else ()),
        realization.foldback_realization_id,
    )
    if realization.realization.local_realization_ids != expected_local_ids:
        raise ValueError("Complete relation must preserve its exact local authorities.")


def validate_materialized_evaluation(
    *,
    request: ConstructionDiscoveryRequest,
    realization: Any,
    evaluation: CombinationEvaluation,
) -> None:
    """Require one materialized route to equal its deterministic evaluation facts."""
    expected_programs = (
        (evaluation.reaction_program, evaluation.end_generation_program)
        if evaluation.end_generation_program is not None
        else (evaluation.reaction_program,)
    )
    expected_assessments = (
        *evaluation.stage_assessments,
        *evaluation.end_generation_stage_assessments,
    )
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        endpoint_matches = (
            realization.final_product.encoding_projection.sequence == evaluation.final_sequence
            and realization.final_product.encoding_projection.source_span
            == evaluation.design_parent_span
        )
    elif request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        endpoint_matches = (
            realization.final_product.reference.sequence == evaluation.final_sequence
            and realization.final_product.encoding_projection.source_span
            == evaluation.design_parent_span
        )
    else:
        endpoint_matches = realization.final_product.reference.sequence == evaluation.final_sequence
    if (
        realization.source_preparation != evaluation.source_preparation
        or tuple(realization.materials[:2]) != (evaluation.source, evaluation.source_complement)
        or realization.construction_program.reaction_programs != expected_programs
        or realization.construction_program.stage_assessments != expected_assessments
        or not endpoint_matches
    ):
        raise ValueError("Materialized realization must equal exact combination evaluation.")


__all__ = [
    "validate_endpoint_evidence",
    "validate_materialized_evaluation",
    "validate_materialized_request",
]
