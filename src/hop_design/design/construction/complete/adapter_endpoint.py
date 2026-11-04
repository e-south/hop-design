"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/adapter_endpoint.py

Builds one exact materialized adapter-ligated hairpin endpoint realization.

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
    MaterializedConstructionRealization,
    MaterializedFinalProduct,
)
from hop_design.models.construction.complete.basal_embedding import basal_nick_boundary
from hop_design.models.construction.complete.evaluation import (
    CombinationEvaluation,
    CompositionRejectionCode,
)
from hop_design.models.construction.complete.evaluation_inputs import (
    derive_complete_payload_source_map,
    derive_linear_source_embedding,
)
from hop_design.models.construction.complete.material import (
    MaterialRouteEntry,
    MaterialUse,
    MaterialUseRole,
)
from hop_design.models.construction.complete.material.functions import material_function_spans
from hop_design.models.construction.complete.material_disposition import (
    derive_route_material_dispositions,
)
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)
from hop_design.models.construction.payload import _content_id
from hop_design.models.construction.realization import FinalProductReference
from hop_design.models.junction import Strand
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import SequenceProjection

from .adapter import materialize_adapter_program


def adapter_realization(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    foldback_result: FoldbackNeighborhoodDiscoveryResult,
    basal_result: BasalNeighborhoodDiscoveryResult,
    evaluation: CombinationEvaluation,
) -> MaterializedConstructionRealization | CompositionRejectionCode:
    """Materialize one exact adapter-ligated hairpin endpoint or return one intrinsic rejection."""
    if evaluation.rejection_reason is not None:
        return evaluation.rejection_reason
    if any(
        item is None
        for item in (
            evaluation.prefix,
            evaluation.source_return_arm,
            evaluation.source,
            evaluation.source_complement,
            evaluation.source_preparation,
            evaluation.adapter,
            evaluation.design_parent_span,
        )
    ):
        raise ValueError("Compatible adapter composition requires every exact route material.")
    prefix = evaluation.prefix
    source_return_arm = evaluation.source_return_arm
    source = evaluation.source
    source_complement = evaluation.source_complement
    source_preparation = evaluation.source_preparation
    adapter = evaluation.adapter
    design_parent_span = evaluation.design_parent_span
    assert prefix is not None and source_return_arm is not None
    assert source is not None and source_complement is not None
    assert source_preparation is not None
    assert adapter is not None
    assert design_parent_span is not None
    if basal.basal_nick.strand is not Strand.BOTTOM:
        raise ValueError("Adapter-route basal opening requires an exact bottom-strand basal nick.")
    basal_nick_boundary(basal, prefix)
    encoding = request.design.plan.hairpin_encoding_insert
    policy = request.materialization.adapter_ligation
    assert policy is not None and evaluation.final_sequence is not None
    material_uses = (
        source_preparation.prepared_top_use,
        source_preparation.prepared_bottom_use,
        MaterialUse.create(
            material_id=adapter.material_id,
            role=MaterialUseRole.LIGATION_ADAPTER,
            specification_resolution_mode=policy.mode,
            route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
        ),
    )
    program = materialize_adapter_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        source_return_arm=source_return_arm,
        source=source,
        source_complement=source_complement,
        adapter=adapter,
        material_uses=material_uses,
        evaluation=evaluation,
        joined_sequence=evaluation.final_sequence,
    )
    functions = material_function_spans(
        material_uses=material_uses, top=program.states[-1].molecules[0], bottom=None
    )
    terminal = program.states[-1]
    reference = FinalProductReference.create(
        endpoint=request.endpoint,
        sequence=terminal.molecules[0].sequence,
        topology="single_stranded_hairpin",
        end_descriptors=tuple(
            end.value
            for strand in terminal.molecules
            for end in (strand.five_prime_end, strand.three_prime_end)
        ),
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
    product = MaterializedFinalProduct(
        reference=reference,
        strands=terminal.molecules,
        encoding_projection=SequenceProjection(
            sequence=encoding.sequence,
            sequence_digest=encoding.sequence_digest,
            source_span=design_parent_span,
            orientation=BindingOrientation.SAME_5TO3,
        ),
        pairings=terminal.pairings,
        material_function_spans=functions,
    )
    materials = (source, source_complement, adapter)
    return MaterializedConstructionRealization.create(
        source_partition_plan=evaluation.source_partition_plan,
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
            source_material_id=source_preparation.source_ssdna.material_id,
        ),
        foldback_realization_id=foldback.foldback_realization_id,
        basal_realization_id=basal.basal_realization_id,
        source_preparation=source_preparation,
        materials=materials,
        material_uses=material_uses,
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
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.RESOLVED,
        ),
        route_material_dispositions=derive_route_material_dispositions(
            materials=materials,
            material_uses=material_uses,
            program=program,
            material_function_spans=functions,
        ),
    )


__all__ = ["adapter_realization"]
