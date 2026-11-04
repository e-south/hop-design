"""Learn exact source-context exclusions from a replayed initial-duplex conflict."""

from typing import Any

from hop_design.models.construction.complete.evaluation import (
    CompositionRejectionCode,
    evaluate_combination,
)
from hop_design.models.construction.complete.evaluation_inputs import (
    derive_linear_source_embedding,
    derive_route_prefix,
)
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
)
from hop_design.models.construction.payload import ConstructionEndpoint, SourceOrientation
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

from ...public import ConstructionCompilation


def context_site_exclusions(receipt: ConstructionCompilation) -> list[dict[str, Any]]:
    """Exclude only the assignments retaining an observed, actionable source site.

    Local authorities and context length fix the unpartitioned initial schedule
    and its declared coordinates. Source preparation must reproduce the exact
    source embedding. Its context variables occur once, forward at the beginning
    or reverse-complemented at the end; all other source positions are fixed.
    A motif predicate at one undeclared actionable window therefore proves a
    necessary rejection for that subset. Other stages, partition plans and direct
    endpoints are deliberately outside this proof. The full compiler still
    decides every surviving completion.
    """
    result = receipt._verified_source().result
    request = result.request
    if (
        result.source_partition_authority is not None
        or request.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
        or not isinstance(
            request.materialization.source_preparation.source_ssdna,
            ConstrainedSourceSsdnaPolicy,
        )
        or len(result.combination_dispositions) != 1
        or result.basal_authority is None
    ):
        return []
    disposition = result.combination_dispositions[0]
    context = disposition.source_context_sequence
    if (
        disposition.rejection_reason is not CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT
        or not context
    ):
        return []
    foldback = next(
        r
        for r in result.foldback_authority.realizations
        if r.foldback_realization_id == disposition.foldback_realization_id
    )
    basal = next(
        r
        for r in result.basal_authority.realizations
        if r.basal_realization_id == disposition.basal_realization_id
    )
    local_prefix = derive_route_prefix(request, basal, foldback.payload_sequence)
    if local_prefix is None:
        return []
    prefix = context + local_prefix
    embedding = derive_linear_source_embedding(
        foldback=foldback, prefix=prefix, source_return_arm=reverse_complement_iupac(prefix)
    )
    foldback_policy = result.foldback_authority.neighborhood.request.enzyme_provisioning
    basal_policy = result.basal_authority.discovery.request.enzyme_provisioning
    evaluation = evaluate_combination(
        request,
        foldback=foldback,
        basal=basal,
        foldback_policy=foldback_policy,
        basal_policy=basal_policy,
        source_context_sequence=context,
        source_partition_plan=None,
    )
    program = evaluation.reaction_program
    if program is None or not program.stages:
        return []
    stage, state = program.stages[0], program.states[0]
    if stage.pre_state_id != state.state_id or len(state.molecules) != 1:
        return []
    molecule = state.molecules[0]
    if (
        molecule.reference_sequence_5prime != embedding.source_sequence
        or molecule.complement_sequence_5prime
        != reverse_complement_iupac(embedding.source_sequence)
        or evaluation.source is None
        or evaluation.source.sequence_5prime != embedding.source_sequence
    ):
        return []
    assessment = next(a for a in evaluation.stage_assessments if a.stage_id == stage.stage_id)
    if assessment.resolved_against_state_id != state.state_id:
        return []
    enzymes = {
        enzyme.enzyme_id: enzyme
        for policy in (foldback_policy, basal_policy)
        for enzyme in policy.catalog.enzymes
    }
    forward = embedding.source_orientation is SourceOrientation.FORWARD
    source = embedding.source_sequence
    exclusions = []
    for binding in assessment.undeclared_bindings:
        if binding.molecule_id != molecule.molecule_id:
            continue
        enzyme = enzymes[binding.enzyme_id]
        motif = enzyme.recognition_pattern
        if binding.orientation is SiteOrientation.REVERSE:
            motif = reverse_complement_iupac(motif)
        start = binding.recognition_span.start.offset
        pattern = ["N"] * len(context)
        for position, symbol in enumerate(motif, start):
            if source[position] not in iupac_bases(symbol):
                raise ValueError("Replayed conflict disagrees with its recognition pattern.")
            index = position if forward else len(source) - 1 - position
            if 0 <= index < len(context):
                pattern[index] = symbol if forward else reverse_complement_iupac(symbol)
        exclusions.append(
            {
                "context_pattern": "".join(pattern),
                "scope": "unpartitioned_initial_source_duplex",
                "stage_id": stage.stage_id,
                "enzyme_id": binding.enzyme_id,
                "recognition_start": start,
                "recognition_end": binding.recognition_span.end.offset,
                "orientation": binding.orientation.value,
            }
        )
    return exclusions
