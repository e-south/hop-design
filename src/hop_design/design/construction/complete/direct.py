"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/direct.py

Composes one exact direct ssDNA-hairpin route from detailed local authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import (
    CompleteConstructionRealization,
    DigitalDesignStatus,
    FinalProductReference,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
)
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    ExactConstructionMaterial,
    MaterializedConstructionRealization,
    MaterializedFinalProduct,
)
from hop_design.models.construction.complete.evaluation import (
    CombinationEvaluation,
    CompositionRejectionCode,
    evaluate_combination,
)
from hop_design.models.construction.complete.evaluation_inputs import (
    derive_complete_payload_source_map,
    derive_linear_source_embedding,
)
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)
from hop_design.models.construction.payload import _content_id
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import SequenceProjection

from .materialization import materialize_direct_program


def _materials(
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
) -> tuple[ExactConstructionMaterial, ...]:
    return source, source_complement


def direct_realization(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord | None,
    foldback_result: FoldbackNeighborhoodDiscoveryResult,
    basal_result: BasalNeighborhoodDiscoveryResult | None,
    evaluation: CombinationEvaluation | None = None,
) -> MaterializedConstructionRealization | CompositionRejectionCode:
    """Materialize one exact direct route or return one stable rejection reason."""
    if evaluation is None:
        evaluation = evaluate_combination(
            request,
            foldback=foldback,
            basal=basal,
            foldback_policy=foldback_result.neighborhood.request.enzyme_provisioning,
            basal_policy=(
                None if basal_result is None else basal_result.discovery.request.enzyme_provisioning
            ),
        )
    if evaluation.rejection_reason is not None:
        return evaluation.rejection_reason
    if (
        evaluation.prefix is None
        or evaluation.source_return_arm is None
        or evaluation.source is None
        or evaluation.source_complement is None
        or evaluation.source_preparation is None
    ):
        raise ValueError("Compatible combination evaluation lacks exact route materials.")
    prefix = evaluation.prefix
    source_return_arm = evaluation.source_return_arm
    source = evaluation.source
    source_complement = evaluation.source_complement
    expected_source = source.sequence_5prime
    materialized = materialize_direct_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        source_return_arm=source_return_arm,
        source=source,
        source_complement=source_complement,
        source_use_id=evaluation.source_preparation.prepared_top_use.use_id,
        source_complement_use_id=evaluation.source_preparation.prepared_bottom_use.use_id,
        evaluation=evaluation,
    )
    if materialized is None:
        raise ValueError("Compatible combination evaluation did not materialize exactly.")
    program, final_strand = materialized
    if final_strand.sequence != evaluation.final_sequence:
        raise ValueError("Materialized endpoint must equal the evaluated final sequence.")
    final_reference = FinalProductReference.create(
        endpoint=request.endpoint,
        sequence=final_strand.sequence,
        topology="single_stranded_hairpin",
        end_descriptors=(
            final_strand.five_prime_end.value,
            final_strand.three_prime_end.value,
        ),
    )
    stage_ids = tuple(
        stage.stage_id for phase in program.reaction_programs for stage in phase.stages
    )
    local_ids = (
        *((basal.basal_realization_id,) if basal is not None else ()),
        foldback.foldback_realization_id,
    )
    complete = CompleteConstructionRealization.create(
        precursor_sequence=expected_source,
        local_realization_ids=local_ids,
        stage_ids=stage_ids,
        final_product_id=final_reference.final_product_id,
    )
    projection = SequenceProjection(
        sequence=final_strand.sequence,
        sequence_digest=request.design.encoding_digest,
        source_span=Span(
            start=Boundary(offset=0),
            end=Boundary(offset=len(final_strand.sequence)),
        ),
        orientation=BindingOrientation.SAME_5TO3,
    )
    embedding = derive_linear_source_embedding(
        foldback=foldback,
        prefix=prefix,
        source_return_arm=source_return_arm,
    )
    source_map = derive_complete_payload_source_map(
        foldback=foldback,
        embedding=embedding,
        source_material_id=evaluation.source_preparation.source_ssdna.material_id,
    )
    geometry_ids = (
        *(
            (
                _content_id(
                    "geometry",
                    1,
                    basal.local_realization.achieved_geometry.model_dump(mode="json"),
                ),
            )
            if basal is not None
            else ()
        ),
        _content_id(
            "geometry",
            1,
            foldback.local_realization.achieved_geometry.model_dump(mode="json"),
        ),
    )
    return MaterializedConstructionRealization.create(
        realization=complete,
        foldback_authority=foldback,
        basal_authority=basal,
        payload_source_map=source_map,
        foldback_realization_id=foldback.foldback_realization_id,
        basal_realization_id=(None if basal is None else basal.basal_realization_id),
        source_preparation=evaluation.source_preparation,
        materials=_materials(source, source_complement),
        material_uses=(
            evaluation.source_preparation.prepared_top_use,
            evaluation.source_preparation.prepared_bottom_use,
        ),
        construction_program=program,
        final_product=MaterializedFinalProduct(
            reference=final_reference,
            strands=(final_strand,),
            encoding_projection=projection,
        ),
        design=request.design,
        geometry_ids=geometry_ids,
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.RESOLVED,
        ),
    )


__all__ = ["direct_realization"]
