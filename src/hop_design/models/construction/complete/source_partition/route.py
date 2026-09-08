"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/route.py

Composes exact cleanup cuts and fragment lineage with local route requirements.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.models.junction import Strand
from hop_design.models.molecular_state import LineageStrand, MaterialBaseLineage, MolecularStrand
from hop_design.models.reactions import ReactionProgram

from ..source_preparation import SourceDuplexPreparationAuthority
from .errors import SourcePartitionBindingError, SourcePartitionBindingFailure
from .facts import partition_fragment_fact, route_cut_facts, route_fragment_fact
from .plan import SourcePartitionPlan
from .reaction import derive_partition_reaction_program


def partitioned_source_strands(
    *,
    plan: SourcePartitionPlan,
    preparation: SourceDuplexPreparationAuthority,
    payload_sequence: str,
    local_program: ReactionProgram,
    required_strands: tuple[MolecularStrand, MolecularStrand],
) -> tuple[ReactionProgram, tuple[MolecularStrand, ...], tuple[MolecularStrand, MolecularStrand]]:
    """Require cleanup to preserve exact local survivors, chemistry, and source mapping."""
    source, complement = (binding.material for binding in preparation.produced_material_bindings)
    expected = plan.request.source
    mapping = plan.request.payload_source_map.segments
    if (
        expected.top_sequence_5prime != source.sequence_5prime
        or expected.top_five_prime_end != source.five_prime_end
        or expected.top_three_prime_end != source.three_prime_end
        or expected.bottom_five_prime_end != complement.five_prime_end
        or expected.bottom_three_prime_end != complement.three_prime_end
        or plan.request.payload.payload.sequence != payload_sequence
        or len(mapping) != 1
        or mapping[0].source_span != preparation.payload_source_span
    ):
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SOURCE_INCOMPATIBLE,
            "Cleanup must act on the same prepared duplex and payload coordinates.",
        )
    if len(local_program.stages) != 1 or any(
        (op.intended_binding.reference_cut is None) == (op.intended_binding.complement_cut is None)
        for op in local_program.stages[0].operations
    ):
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.STAGE_INCOMPATIBLE,
            "Concurrent source partition requires one local nick-only stage.",
        )
    program = derive_partition_reaction_program(plan.realization)
    definitions = plan.request.enzyme_provisioning.catalog.enzymes
    if not route_cut_facts(local_program, definitions) <= route_cut_facts(program, definitions):
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.CUT_INCOMPATIBLE,
            "Cleanup must include every locally required nick with its exact binding.",
        )
    top_use = preparation.prepared_top_use.use_id
    bottom_use = preparation.prepared_bottom_use.use_id
    source_length = len(source.sequence_5prime)
    strands = []
    for fragment in plan.realization.denatured.fragments:
        top = fragment.precursor_strand is Strand.TOP
        start = (
            fragment.precursor_span.start.offset
            if top
            else source_length - fragment.precursor_span.end.offset
        )
        strands.append(
            MolecularStrand(
                strand_id=fragment.fragment_id,
                sequence=fragment.sequence,
                five_prime_end=fragment.five_prime_end,
                three_prime_end=fragment.three_prime_end,
                lineage=tuple(
                    MaterialBaseLineage(
                        product_index=index,
                        origin_id=top_use if top else bottom_use,
                        origin_strand=LineageStrand.PRIMARY if top else LineageStrand.COMPLEMENTARY,
                        origin_index=start + index,
                    )
                    for index in range(len(fragment.sequence))
                ),
            )
        )
    retained = {
        partition_fragment_fact(fragment): strand
        for fragment, strand in zip(plan.realization.denatured.fragments, strands, strict=True)
        if fragment.fragment_id in plan.realization.selected.retained_fragment_ids
    }
    required = tuple(
        route_fragment_fact(
            strand,
            source_length=source_length,
            top_use_id=top_use,
            bottom_use_id=bottom_use,
        )
        for strand in required_strands
    )
    if len(retained) != 2 or set(required) != set(retained):
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
            "Cleanup survivors must equal the strands required for foldback and adapter joining.",
        )
    return program, tuple(strands), (retained[required[0]], retained[required[1]])
