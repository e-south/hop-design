"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/pcr.py

Materializes one exact basal-open hairpin PCR construction endpoint.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.complete import (
    ConstructionProgram,
    ConstructionState,
    ConstructionStatePhase,
    ConstructionTransition,
    ConstructionTransitionKind,
    ExactConstructionMaterial,
    MaterialUse,
    PcrPrimer,
    PrimerExtensionAuthority,
)
from hop_design.models.construction.complete.evaluation import CombinationEvaluation
from hop_design.models.construction.complete.material.functions import material_function_spans
from hop_design.models.construction.complete.pcr.products import (
    endpoint_fate_spans,
    pcr_products,
)
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_replay import observe_pair
from hop_design.models.molecular_state import (
    PrimerBinding,
)
from hop_design.models.plan import SequenceFeature

from .adapter import materialize_adapter_program


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def materialize_pcr_program(
    *,
    foldback: FoldbackLocalRealization,
    basal: BasalRealizationRecord,
    prefix: str,
    source_return_arm: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
    adapter: ExactConstructionMaterial,
    forward_primer: PcrPrimer,
    reverse_primer: PcrPrimer,
    material_uses: tuple[MaterialUse, MaterialUse, MaterialUse, MaterialUse, MaterialUse],
    evaluation: CombinationEvaluation,
    encoding_features: tuple[SequenceFeature, ...],
    design_endpoint_span: Span,
    endpoint_retained_spans: tuple[Span, Span] | None = None,
) -> tuple[ConstructionProgram, PrimerExtensionAuthority]:
    """Materialize the exact basal-open intermediate through the PCR duplex."""
    if evaluation.pcr_template_sequence is None:
        raise ValueError("PCR materialization requires the exact joined template.")
    prefix_program = materialize_adapter_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        source_return_arm=source_return_arm,
        source=source,
        source_complement=source_complement,
        adapter=adapter,
        material_uses=(material_uses[0], material_uses[1], material_uses[2]),
        evaluation=evaluation,
        joined_sequence=evaluation.pcr_template_sequence,
    )
    adapter_ligated = prefix_program.states[-1]
    ligated = adapter_ligated.molecules[0]
    forward_use, reverse_use = material_uses[3:]
    top, bottom = pcr_products(
        ligated,
        forward_primer,
        reverse_primer,
        forward_use_id=forward_use.use_id,
        reverse_use_id=reverse_use.use_id,
    )
    duplex_pairs = tuple(
        observe_pair(
            left_strand_id=top.strand_id,
            right_strand_id=bottom.strand_id,
            left_index=index,
            right_index=len(top.sequence) - 1 - index,
            left_base=base,
            right_base=bottom.sequence[len(top.sequence) - 1 - index],
        )
        for index, base in enumerate(top.sequence)
    )
    pcr_state = ConstructionState.create(
        molecules=(top, bottom),
        phase=ConstructionStatePhase.HAIRPIN_PCR_DUPLEX,
        pairings=duplex_pairs,
    )
    bindings = (
        PrimerBinding(
            binding_id="complete-forward-primer-binding",
            primer_id=forward_use.use_id,
            template_strand_id=f"{ligated.strand_id}-derived-complement",
            template_span=_span(
                len(ligated.sequence) - forward_primer.annealing_length_nt,
                len(ligated.sequence),
            ),
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
        PrimerBinding(
            binding_id="complete-reverse-primer-binding",
            primer_id=reverse_use.use_id,
            template_strand_id=ligated.strand_id,
            template_span=_span(
                len(ligated.sequence) - reverse_primer.annealing_length_nt,
                len(ligated.sequence),
            ),
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
    )
    functions = material_function_spans(
        material_uses=material_uses,
        top=top,
        bottom=bottom,
    )
    fates = endpoint_fate_spans(
        encoding_features,
        len(top.sequence),
        design_source_span=design_endpoint_span,
        retained_parent_spans=endpoint_retained_spans,
    )
    extension = PrimerExtensionAuthority.create(
        pre_state_id=adapter_ligated.state_id,
        post_state_id=pcr_state.state_id,
        forward_primer=forward_primer,
        reverse_primer=reverse_primer,
        forward_primer_use=forward_use,
        reverse_primer_use=reverse_use,
        material_uses=material_uses,
        bindings=bindings,
        products=(top, bottom),
        pairings=duplex_pairs,
        material_function_spans=functions,
        endpoint_sequence_fate_spans=fates,
    )
    return ConstructionProgram.create(
        states=(*prefix_program.states, pcr_state),
        transitions=(
            *prefix_program.transitions,
            ConstructionTransition.create(
                kind=ConstructionTransitionKind.PRIMER_EXTENSION,
                pre_state_id=adapter_ligated.state_id,
                post_state_id=pcr_state.state_id,
                pcr_authority=extension,
            ),
        ),
        reaction_programs=prefix_program.reaction_programs,
        stage_assessments=prefix_program.stage_assessments,
    ), extension


__all__ = ["materialize_pcr_program"]
