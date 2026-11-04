"""Locate rejected actionable sites by replaying the existing molecular evaluator."""

from typing import Any

from hop_design.models.construction.complete.evaluation import (
    CompositionRejectionCode,
    evaluate_combination,
)
from hop_design.models.construction.complete.source_partition.plan import selected_partition_plan

from ..public import ConstructionCompilation, VerifiedConstructionBundle


def actionable_site_conflicts(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> list[dict[str, Any]]:
    result = receipt._verified_source().result
    rejected = [
        d
        for d in result.combination_dispositions
        if d.rejection_reason is CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT
    ]
    if not rejected:
        return []
    foldbacks = {r.foldback_realization_id: r for r in result.foldback_authority.realizations}
    basals = (
        {}
        if result.basal_authority is None
        else {r.basal_realization_id: r for r in result.basal_authority.realizations}
    )
    foldback_policy = result.foldback_authority.neighborhood.request.enzyme_provisioning
    basal_policy = (
        None
        if result.basal_authority is None
        else result.basal_authority.discovery.request.enzyme_provisioning
    )
    release_policy = (
        None if result.request.release is None else result.request.release.enzyme_provisioning
    )
    names = {
        enzyme.enzyme_id: enzyme.canonical_name
        for policy in (foldback_policy, basal_policy, release_policy)
        if policy is not None
        for enzyme in policy.catalog.enzymes
    }
    plan = selected_partition_plan(
        result.source_partition_authority, result.request.selected_source_partition_realization_id
    )
    sites = []
    for disposition in rejected:
        evaluation = evaluate_combination(
            result.request,
            foldback=foldbacks[disposition.foldback_realization_id],
            basal=None
            if disposition.basal_realization_id is None
            else basals[disposition.basal_realization_id],
            foldback_policy=foldback_policy,
            basal_policy=basal_policy,
            source_context_sequence=disposition.source_context_sequence,
            source_partition_plan=plan,
        )
        for phase, program, assessments in (
            ("construction", evaluation.reaction_program, evaluation.stage_assessments),
            (
                "end_generation",
                evaluation.end_generation_program,
                evaluation.end_generation_stage_assessments,
            ),
        ):
            if program is None:
                continue
            states = {s.state_id: s for s in program.states}
            for assessment in assessments:
                state = states[assessment.resolved_against_state_id]
                for binding in assessment.undeclared_bindings:
                    molecule = state.by_id(binding.molecule_id)
                    start, end = (
                        binding.recognition_span.start.offset,
                        binding.recognition_span.end.offset,
                    )
                    sites.append(
                        {
                            "combination_ordinal": disposition.ordinal,
                            "processing_phase": phase,
                            "stage_id": assessment.stage_id,
                            "state_id": state.state_id,
                            "molecule_id": binding.molecule_id,
                            "enzyme_id": binding.enzyme_id,
                            "enzyme_name": names[binding.enzyme_id],
                            "recognition_start": start,
                            "recognition_end": end,
                            "recognition_sequence": molecule.reference_sequence_5prime[start:end],
                            "orientation": binding.orientation.value,
                            "reference_cut": None
                            if binding.reference_cut is None
                            else binding.reference_cut.offset,
                            "complement_cut": None
                            if binding.complement_cut is None
                            else binding.complement_cut.offset,
                            "coordinate_convention": "zero_based_half_open_reference_strand",
                        }
                    )
    return sites
