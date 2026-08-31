"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/clone_endpoint.py

Builds one exact destination-neutral clone-ready duplex realization.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import (
    CompleteConstructionRealization,
    DigitalDesignStatus,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
)
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    ConstructionProgram,
    ConstructionState,
    ConstructionStatePhase,
    ConstructionTransition,
    ConstructionTransitionKind,
    DuplexFinalProductReference,
    MaterializedConstructionRealization,
    MaterializedFinalProduct,
    ReactionBoundaryMapping,
)
from hop_design.models.construction.complete.clone import (
    CloneEndGenerationError,
    clone_endpoint_fate_spans,
    derive_clone_digest,
    derive_clone_end_program,
)
from hop_design.models.construction.complete.evaluation import (
    CombinationEvaluation,
    CompositionRejectionCode,
)
from hop_design.models.construction.complete.evaluation_inputs import (
    derive_complete_payload_source_map,
    derive_linear_source_embedding,
)
from hop_design.models.construction.complete.material_disposition import (
    derive_route_material_dispositions,
)
from hop_design.models.construction.complete.pcr.products import material_function_spans
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)
from hop_design.models.construction.payload import _content_id
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import SequenceProjection

from .pcr import materialize_pcr_program


def clone_realization(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    foldback_result: FoldbackNeighborhoodDiscoveryResult,
    basal_result: BasalNeighborhoodDiscoveryResult,
    evaluation: CombinationEvaluation,
) -> MaterializedConstructionRealization | CompositionRejectionCode:
    """Materialize one exact clone-ready endpoint or return one intrinsic rejection."""
    if evaluation.rejection_reason is not None:
        return evaluation.rejection_reason
    if any(
        item is None
        for item in (
            evaluation.prefix,
            evaluation.source_return_arm,
            evaluation.source,
            evaluation.source_complement,
            evaluation.pcr_template_sequence,
            evaluation.design_parent_span,
            evaluation.end_generation_program,
            evaluation.end_generation_bindings,
            request.materialization.adapter,
            request.materialization.forward_primer,
            request.materialization.reverse_primer,
        )
    ):
        raise ValueError("Compatible clone composition requires every exact route authority.")
    prefix = evaluation.prefix
    source_return_arm = evaluation.source_return_arm
    source = evaluation.source
    source_complement = evaluation.source_complement
    design_parent_span = evaluation.design_parent_span
    end_generation_program = evaluation.end_generation_program
    end_generation_bindings = evaluation.end_generation_bindings
    adapter = request.materialization.adapter
    forward = request.materialization.forward_primer
    reverse = request.materialization.reverse_primer
    assert prefix is not None and source_return_arm is not None
    assert source is not None and source_complement is not None
    assert design_parent_span is not None and end_generation_program is not None
    assert end_generation_bindings is not None
    assert adapter is not None and forward is not None and reverse is not None
    if basal.basal_nick.strand is not Strand.BOTTOM:
        raise ValueError("Clone basal opening requires one exact bottom-strand nick.")
    encoding = request.design.plan.hairpin_encoding_insert
    template_sequence = evaluation.pcr_template_sequence
    assert template_sequence is not None
    template_design_start = template_sequence.find(encoding.sequence)
    if (
        template_design_start < 0
        or template_sequence.find(encoding.sequence, template_design_start + 1) >= 0
    ):
        return CompositionRejectionCode.CLONE_END_GENERATION_INCOMPATIBLE
    pcr_program, _ = materialize_pcr_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        source_return_arm=source_return_arm,
        source=source,
        source_complement=source_complement,
        adapter=adapter,
        forward_primer=forward,
        reverse_primer=reverse,
        evaluation=evaluation,
        encoding_features=encoding.features,
        design_endpoint_span=Span(
            start=Boundary(offset=template_design_start + len(forward.five_prime_handle)),
            end=Boundary(
                offset=(
                    template_design_start + len(forward.five_prime_handle) + len(encoding.sequence)
                )
            ),
        ),
    )
    pcr_state = pcr_program.states[-1]
    try:
        digest = derive_clone_digest(
            bindings=end_generation_bindings,
            pcr_state=pcr_state,
            design_sequence=request.design.encoding_sequence,
            design_digest=request.design.encoding_digest,
        )
        replayed_end_program = derive_clone_end_program(
            pcr_state=pcr_state,
            digest=digest,
        )
    except CloneEndGenerationError:
        return CompositionRejectionCode.CLONE_END_GENERATION_INCOMPATIBLE
    if replayed_end_program != end_generation_program:
        return CompositionRejectionCode.CLONE_END_GENERATION_INCOMPATIBLE
    terminal = ConstructionState.create(
        molecules=digest.strands,
        phase=ConstructionStatePhase.CLONE_READY_DUPLEX,
        pairings=digest.pairings,
    )
    boundary = ReactionBoundaryMapping.create(
        reaction_program_id=end_generation_program.program_id,
        pre_state_id=pcr_state.state_id,
        post_state_id=terminal.state_id,
        pre_strands=pcr_state.molecules,
        post_strands=terminal.molecules,
        pre_pairings=pcr_state.pairings,
        post_pairings=terminal.pairings,
        pre_bonds=pcr_state.formed_bonds,
        post_bonds=terminal.formed_bonds,
    )
    end_transition = ConstructionTransition.create(
        kind=ConstructionTransitionKind.END_GENERATION,
        pre_state_id=pcr_state.state_id,
        post_state_id=terminal.state_id,
        reaction_program_id=end_generation_program.program_id,
        reaction_boundary_mapping=boundary,
    )
    program = ConstructionProgram.create(
        states=(*pcr_program.states, terminal),
        transitions=(*pcr_program.transitions, end_transition),
        reaction_programs=(*pcr_program.reaction_programs, end_generation_program),
        stage_assessments=(
            *pcr_program.stage_assessments,
            *evaluation.end_generation_stage_assessments,
        ),
    )
    reference = DuplexFinalProductReference.create(
        endpoint=request.endpoint,
        sequence=terminal.molecules[0].sequence,
        topology="linear_duplex",
        end_descriptors=tuple(
            end.value
            for strand in terminal.molecules
            for end in (strand.five_prime_end, strand.three_prime_end)
        ),
        strands=terminal.molecules,
        pairings=terminal.pairings,
        cohesive_ends=digest.cohesive_ends,
    )
    functions = material_function_spans(
        materials=(source, source_complement, adapter, forward.oligo, reverse.oligo),
        top=terminal.molecules[0],
        bottom=terminal.molecules[1],
    )
    fates = clone_endpoint_fate_spans(features=encoding.features, digest=digest)
    product = MaterializedFinalProduct(
        reference=reference,
        strands=terminal.molecules,
        encoding_projection=SequenceProjection(
            sequence=encoding.sequence,
            sequence_digest=encoding.sequence_digest,
            source_span=digest.encoding_projection.source_span,
            orientation=digest.encoding_projection.orientation,
        ),
        pairings=terminal.pairings,
        cohesive_ends=digest.cohesive_ends,
        material_function_spans=functions,
        endpoint_sequence_fate_spans=fates,
    )
    local_ids = (basal.basal_realization_id, foldback.foldback_realization_id)
    complete = CompleteConstructionRealization.create(
        precursor_sequence=source.sequence_5prime,
        local_realization_ids=local_ids,
        stage_ids=tuple(
            stage.stage_id for phase in program.reaction_programs for stage in phase.stages
        ),
        final_product_id=reference.final_product_id,
    )
    materials = (source, source_complement, adapter, forward.oligo, reverse.oligo)
    return MaterializedConstructionRealization.create(
        realization=complete,
        foldback_authority=foldback,
        basal_authority=basal,
        payload_source_map=derive_complete_payload_source_map(
            foldback=foldback,
            embedding=derive_linear_source_embedding(
                foldback=foldback,
                prefix=prefix,
                source_return_arm=source_return_arm,
            ),
            source_material_id=source.material_id,
        ),
        foldback_realization_id=foldback.foldback_realization_id,
        basal_realization_id=basal.basal_realization_id,
        materials=materials,
        construction_program=program,
        final_product=product,
        design=request.design,
        geometry_ids=(
            _content_id(
                "geometry",
                1,
                basal.local_realization.achieved_geometry.model_dump(mode="json"),
            ),
            _content_id(
                "geometry",
                1,
                foldback.local_realization.achieved_geometry.model_dump(mode="json"),
            ),
        ),
        relaxation_radii=(basal.relaxation_radius, foldback.relaxation_radius),
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.RESOLVED,
        ),
        route_material_dispositions=derive_route_material_dispositions(
            materials=materials,
            program=program,
            material_function_spans=functions,
        ),
    )


__all__ = ["clone_realization"]
