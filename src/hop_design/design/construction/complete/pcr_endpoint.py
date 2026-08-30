"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/pcr_endpoint.py

Builds one exact materialized hairpin PCR endpoint realization.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import (
    CompleteConstructionRealization,
    DigitalDesignStatus,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    PayloadSourceMap,
    PayloadSourceSegment,
    SourceOrientation,
)
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    DuplexFinalProductReference,
    MaterializedConstructionRealization,
    MaterializedFinalProduct,
)
from hop_design.models.construction.complete.evaluation import (
    CombinationEvaluation,
    CompositionRejectionCode,
)
from hop_design.models.construction.complete.material_disposition import (
    derive_route_material_dispositions,
)
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)
from hop_design.models.construction.payload import _content_id
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import SequenceProjection

from .pcr import materialize_pcr_program


def pcr_realization(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    foldback_result: FoldbackNeighborhoodDiscoveryResult,
    basal_result: BasalNeighborhoodDiscoveryResult,
    evaluation: CombinationEvaluation,
) -> MaterializedConstructionRealization | CompositionRejectionCode:
    """Materialize one exact PCR endpoint or return one intrinsic rejection."""
    if evaluation.rejection_reason is not None:
        return evaluation.rejection_reason
    if any(
        item is None
        for item in (
            evaluation.prefix,
            evaluation.return_arm,
            evaluation.source,
            evaluation.source_complement,
            request.materialization.adapter,
            request.materialization.forward_primer,
            request.materialization.reverse_primer,
        )
    ):
        raise ValueError("Compatible PCR composition requires every exact route material.")
    prefix = evaluation.prefix
    return_arm = evaluation.return_arm
    source = evaluation.source
    source_complement = evaluation.source_complement
    adapter = request.materialization.adapter
    forward = request.materialization.forward_primer
    reverse = request.materialization.reverse_primer
    assert prefix is not None and return_arm is not None
    assert source is not None and source_complement is not None
    assert adapter is not None and forward is not None and reverse is not None
    if basal.basal_nick.strand is not Strand.BOTTOM:
        raise ValueError("PCR basal opening requires an exact bottom-strand basal nick.")
    if basal.basal_nick.boundary.offset != len(prefix):
        raise ValueError("PCR basal nick must equal the exact aligned prefix boundary.")
    encoding = request.design.plan.hairpin_encoding_insert
    program, extension = materialize_pcr_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        return_arm=return_arm,
        source=source,
        source_complement=source_complement,
        adapter=adapter,
        forward_primer=forward,
        reverse_primer=reverse,
        evaluation=evaluation,
        encoding_features=encoding.features,
        design_source_span=Span(
            start=Boundary(offset=0),
            end=Boundary(offset=len(encoding.sequence)),
        ),
    )
    terminal = program.states[-1]
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
        cohesive_ends=(),
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
            source_span=Span(
                start=Boundary(offset=0),
                end=Boundary(offset=len(encoding.sequence)),
            ),
            orientation=BindingOrientation.SAME_5TO3,
        ),
        pairings=terminal.pairings,
        material_function_spans=extension.material_function_spans,
        endpoint_sequence_fate_spans=extension.endpoint_sequence_fate_spans,
    )
    materials = (source, source_complement, adapter, forward, reverse)
    return MaterializedConstructionRealization.create(
        realization=complete,
        foldback_authority=foldback,
        basal_authority=basal,
        payload_source_map=PayloadSourceMap(
            segments=(
                PayloadSourceSegment(
                    payload_span=Span(
                        start=request.payload.basal_boundary,
                        end=request.payload.foldback_boundary,
                    ),
                    source_material_id=source.material_id,
                    source_span=Span(
                        start=Boundary(offset=len(prefix)),
                        end=Boundary(offset=len(prefix) + len(foldback.payload_sequence)),
                    ),
                    orientation=SourceOrientation.FORWARD,
                ),
            )
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
            material_function_spans=extension.material_function_spans,
        ),
    )


__all__ = ["pcr_realization"]
