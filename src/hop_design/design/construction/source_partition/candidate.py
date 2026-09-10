"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/source_partition/candidate.py

Derives source-removal inputs for one examined PCR-bearing combination.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.models.construction.complete import ConstructionSpaceResult
from hop_design.models.construction.complete.evaluation.context import (
    PreparedContext,
    build_combination_context,
    prepare_context,
)
from hop_design.models.construction.complete.evaluation_inputs import (
    derive_complete_payload_source_map,
    replay_linear_source_embedding,
)
from hop_design.models.construction.complete.pcr.source import derive_pcr_source
from hop_design.models.construction.complete.source_preparation import (
    SourceDuplexPreparationAuthority,
)
from hop_design.models.construction.payload import ConstructionEndpoint, PayloadSourceMap
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import MolecularStrand


def prepare_combination_source(
    result: ConstructionSpaceResult, ordinal: int
) -> tuple[SourceDuplexPreparationAuthority, PayloadSourceMap, tuple[MolecularStrand, ...]]:
    """Replay source preparation and local survivor requirements, not route acceptance."""
    if type(ordinal) is not int or not 0 <= ordinal < len(result.combination_dispositions):
        raise ValueError("Source-removal selection must name an examined combination ordinal.")
    choice = result.combination_dispositions[ordinal]
    if (
        result.request.endpoint
        not in {
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            ConstructionEndpoint.CLONE_READY_DUPLEX,
        }
        or result.basal_authority is None
    ):
        raise ValueError("Combination source removal requires a PCR-bearing endpoint.")
    foldback = next(
        item
        for item in result.foldback_authority.realizations
        if item.foldback_realization_id == choice.foldback_realization_id
    )
    basal = next(
        item
        for item in result.basal_authority.realizations
        if item.basal_realization_id == choice.basal_realization_id
    )
    if basal.basal_nick.strand is not Strand.BOTTOM:
        raise ValueError("Combination source removal requires the PCR-compatible basal strand.")
    context = prepare_context(
        build_combination_context(
            result.request,
            foldback=foldback,
            basal=basal,
            foldback_policy=result.foldback_authority.neighborhood.request.enzyme_provisioning,
            basal_policy=result.basal_authority.discovery.request.enzyme_provisioning,
            source_context_sequence=choice.source_context_sequence,
            source_partition_plan=None,
        )
    )
    if not isinstance(context, PreparedContext):
        raise ValueError(f"Combination source preparation failed: {context.rejection_reason}.")
    source = derive_pcr_source(
        foldback=foldback, basal=basal, preparation=context.source_preparation, partition=None
    )
    _, _, embedding = replay_linear_source_embedding(
        foldback=foldback,
        source_sequence=context.source.sequence_5prime,
        complement_sequence=context.source_complement.sequence_5prime,
    )
    mapping = derive_complete_payload_source_map(
        foldback=foldback, embedding=embedding, source_material_id="source-duplex"
    )
    return context.source_preparation, mapping, source.selected
