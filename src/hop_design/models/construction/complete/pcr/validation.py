"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pcr/validation.py

Validates exact hairpin PCR endpoint chronology and molecular authority.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.construction.targets import BasalPairClass
from hop_design.models.junction import Strand
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.physical import JunctionPairKind
from hop_design.models.sequence import reverse_complement_iupac

from ..evaluation.result import CompositionRejectionCode
from ..evaluation_inputs import replay_linear_source_embedding
from ..material import ExactConstructionMaterial, PcrPrimer
from ..state import ConstructionStatePhase
from ..transition import ConstructionTransitionKind
from .authority import (
    AdapterAnnealingAuthority,
    DuplexFinalProductReference,
    PrimerExtensionAuthority,
)
from .products import endpoint_fate_spans, material_function_spans
from .route import pcr_cleaved_strands, select_pcr_fragments
from .schedule import derive_pcr_reaction_program

if TYPE_CHECKING:
    from ..realization import MaterializedConstructionRealization


def evaluate_pcr_compatibility(
    *,
    basal: BasalRealizationRecord | None,
    prefix: str,
    pcr_template: str,
    adapter: ExactConstructionMaterial,
    forward: PcrPrimer,
    reverse: PcrPrimer,
) -> CompositionRejectionCode | None:
    """Return the first closed rejection for one exact PCR route context."""
    if (
        basal is None
        or basal.basal_nick.strand is not Strand.BOTTOM
        or basal.basal_nick.boundary.offset != len(prefix)
    ):
        return CompositionRejectionCode.PCR_BASAL_OPEN_INCOMPATIBLE
    local_adapter = next(
        (item for item in basal.materials if item.material_id == "ligation-adapter"),
        None,
    )
    profile = basal.projection.pairing_profile
    if (
        adapter is None
        or local_adapter is None
        or profile is None
        or profile.adapter_span.end.offset > len(adapter.sequence_5prime)
        or adapter.sequence_5prime[
            profile.adapter_span.start.offset : profile.adapter_span.end.offset
        ]
        != local_adapter.sequence_5prime
        or adapter.five_prime_end is not EndChemistry.PHOSPHATE
        or adapter.three_prime_end is not EndChemistry.HYDROXYL
    ):
        return CompositionRejectionCode.PCR_ADAPTER_MISMATCH
    complex_state = basal.adapter_annealed_complex
    if (
        profile is None
        or complex_state is None
        or profile.adapter_span.end.offset > len(adapter.sequence_5prime)
        or tuple(
            (
                pair.left_index - profile.source_span.start.offset,
                pair.right_index,
                pair.left_base,
                pair.right_base,
            )
            for pair in complex_state.pairs
        )
        != tuple(
            (
                pair.source_index,
                pair.adapter_index,
                pair.source_base,
                pair.adapter_base,
            )
            for pair in profile.pairs
        )
    ):
        return CompositionRejectionCode.PCR_PAIRING_PROFILE_MISMATCH
    if (
        forward.oligo.three_prime_end is not EndChemistry.HYDROXYL
        or reverse.oligo.three_prime_end is not EndChemistry.HYDROXYL
        or forward.annealing_sequence != pcr_template[: forward.annealing_length_nt]
        or reverse.annealing_sequence
        != reverse_complement_iupac(pcr_template[-reverse.annealing_length_nt :])
    ):
        return CompositionRejectionCode.PCR_PRIMER_MISMATCH
    return None


def validate_adapter_pairing_profile(
    authority: AdapterAnnealingAuthority,
    *,
    basal: BasalRealizationRecord,
    closed_strand_id: str,
    adapter_strand_id: str,
) -> None:
    """Replay literal H5 pair coordinates, bases, and classes into PCR authority."""
    profile = basal.projection.pairing_profile
    if profile is None:
        raise ValueError("PCR route requires the exact basal adapter-pairing authority.")
    kind_by_class = {
        BasalPairClass.MATCH: JunctionPairKind.WATSON_CRICK,
        BasalPairClass.WOBBLE: JunctionPairKind.GT_WOBBLE,
        BasalPairClass.MISMATCH: JunctionPairKind.HARD_MISMATCH,
    }
    expected = tuple(
        (
            closed_strand_id,
            adapter_strand_id,
            pair.source_index + profile.source_span.start.offset,
            pair.adapter_index,
            pair.source_base,
            pair.adapter_base,
            kind_by_class[pair.pair_class],
        )
        for pair in profile.pairs
    )
    observed = tuple(
        (
            pair.left_strand_id,
            pair.right_strand_id,
            pair.left_index,
            pair.right_index,
            pair.left_base,
            pair.right_base,
            pair.kind,
        )
        for pair in authority.pairings
    )
    if (
        authority.hairpin_span != profile.source_span
        or authority.adapter_span != profile.adapter_span
        or observed != expected
    ):
        raise ValueError("PCR adapter annealing must replay the exact H5 pairing profile.")


def validate_pcr_realization(realization: MaterializedConstructionRealization) -> None:
    """Require the exact PCR phases, authority, duplex, and design subspan."""
    item = realization
    program = item.construction_program
    basal = item.basal_authority
    if basal is None or basal.basal_nick.strand is not Strand.BOTTOM:
        raise ValueError("PCR route requires one exact bottom-strand basal nick authority.")
    source, source_complement = item.materials[:2]
    source_use, source_complement_use = item.material_uses[:2]
    prefix, source_return_arm, _ = replay_linear_source_embedding(
        foldback=item.foldback_authority,
        source_sequence=source.sequence_5prime,
        complement_sequence=source_complement.sequence_5prime,
    )
    if source_return_arm != reverse_complement_iupac(prefix):
        raise ValueError(
            "PCR source-return arm must be the reverse complement of the retained prefix."
        )
    prefix_length = len(prefix)
    if basal.basal_nick.boundary.offset != prefix_length:
        raise ValueError("PCR basal nick must equal the exact aligned prefix boundary.")
    expected_reaction = derive_pcr_reaction_program(
        foldback=item.foldback_authority,
        basal=basal,
        prefix=prefix,
        source_return_arm=source_return_arm,
        source=source,
        source_complement=source_complement,
    )
    if not program.reaction_programs or program.reaction_programs[0] != expected_reaction:
        raise ValueError("PCR enzyme phase must replay the exact basal-open local authorities.")
    expected_cleaved = pcr_cleaved_strands(
        expected_reaction,
        foldback=item.foldback_authority,
        prefix_length=prefix_length,
        source=source,
        source_complement=source_complement,
        source_use_id=source_use.use_id,
        source_complement_use_id=source_complement_use.use_id,
    )
    if program.states[1].molecules != expected_cleaved:
        raise ValueError("PCR cleaved strands must replay exact source-fragment authorities.")
    if (
        program.states[2].molecules != expected_cleaved
        or program.states[2].pairings
        or program.states[2].formed_bonds
    ):
        raise ValueError("PCR denaturation may only remove duplex associations.")
    expected_selected = select_pcr_fragments(
        expected_cleaved,
        foldback=item.foldback_authority,
        source_material_use_id=source_use.use_id,
        source_complement_material_use_id=source_complement_use.use_id,
        source_return_arm=source_return_arm,
    )
    if program.states[3].molecules != expected_selected:
        raise ValueError("PCR selection must retain the exact source and foldback fragments.")
    pcr_indexes = tuple(
        index
        for index, state in enumerate(program.states)
        if state.phase is ConstructionStatePhase.HAIRPIN_PCR_DUPLEX
    )
    if len(pcr_indexes) != 1:
        raise ValueError("PCR-bearing routes require one exact PCR duplex state.")
    pcr_index = pcr_indexes[0]
    expected_tail = (
        ConstructionStatePhase.FOLDBACK_CLOSED_HAIRPIN,
        ConstructionStatePhase.ADAPTER_ANNEALED,
        ConstructionStatePhase.ADAPTER_LIGATED,
        ConstructionStatePhase.HAIRPIN_PCR_DUPLEX,
    )
    actual_tail = tuple(state.phase for state in program.states[pcr_index - 3 : pcr_index + 1])
    if actual_tail != expected_tail:
        raise ValueError("PCR route must preserve exact foldback, adapter, and duplex phases.")
    if item.final_product.reference.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX and any(
        transition.kind is ConstructionTransitionKind.END_GENERATION
        for transition in program.transitions
    ):
        raise ValueError("A PCR endpoint cannot contain end-generation evidence.")
    adapter_transition = program.transitions[pcr_index - 3]
    adapter_authority = adapter_transition.pcr_authority
    if not isinstance(adapter_authority, AdapterAnnealingAuthority):
        raise ValueError("PCR route requires the exact basal adapter-pairing authority.")
    closed, adapter_strand = program.states[pcr_index - 2].molecules
    validate_adapter_pairing_profile(
        adapter_authority,
        basal=basal,
        closed_strand_id=closed.strand_id,
        adapter_strand_id=adapter_strand.strand_id,
    )
    terminal_transition = program.transitions[pcr_index - 1]
    if not isinstance(terminal_transition.pcr_authority, PrimerExtensionAuthority):
        raise ValueError("PCR endpoint requires one exact primer-extension authority.")
    product = item.final_product
    reference = product.reference
    pcr_state = program.states[pcr_index]
    if reference.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        if (
            not isinstance(reference, DuplexFinalProductReference)
            or reference.topology != "linear_duplex"
            or product.strands != pcr_state.molecules
            or product.pairings != pcr_state.pairings
            or product.cohesive_ends
        ):
            raise ValueError("PCR endpoint must equal its exact terminal duplex graph.")
        projection = product.encoding_projection
        if (
            projection.orientation is not BindingOrientation.SAME_5TO3
            or projection.source_span.end.offset > len(product.strands[0].sequence)
            or product.strands[0].sequence[
                projection.source_span.start.offset : projection.source_span.end.offset
            ]
            != projection.sequence
        ):
            raise ValueError("PCR design encoding must be an exact top-strand subspan.")
        if (
            projection.sequence != item.design.encoding_sequence
            or projection.sequence_digest != item.design.encoding_digest
        ):
            raise ValueError("PCR endpoint encoding projection must equal the verified design.")
    extension = terminal_transition.pcr_authority
    expected_functions = material_function_spans(
        material_uses=item.material_uses,
        top=pcr_state.molecules[0],
        bottom=pcr_state.molecules[1],
    )
    if extension.material_function_spans != expected_functions:
        raise ValueError("PCR material-function spans must replay exact retained lineage.")
    expected_fates = endpoint_fate_spans(
        item.design.plan.hairpin_encoding_insert.features,
        len(pcr_state.molecules[0].sequence),
        design_source_span=product.encoding_projection.source_span,
    )
    if extension.endpoint_sequence_fate_spans != expected_fates:
        raise ValueError("PCR sequence-fate spans must replay exact design features.")
    if reference.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        if product.material_function_spans != expected_functions:
            raise ValueError("PCR material-function spans must replay exact retained lineage.")
        if product.endpoint_sequence_fate_spans != expected_fates:
            raise ValueError("PCR sequence-fate spans must replay exact design features.")


__all__ = [
    "evaluate_pcr_compatibility",
    "validate_adapter_pairing_profile",
    "validate_pcr_realization",
]
