"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/clone/validation.py

Replays exact clone-ready chronology, digestion, and endpoint evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hop_design.models.construction.enzyme_binding import ConstructionEnzymeBinding
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.enzymes import EnzymeRole

from ..pcr import DuplexFinalProductReference
from ..pcr.products import material_function_spans
from ..pcr.validation import validate_pcr_realization
from ..state import ConstructionStatePhase
from ..transition import ConstructionTransitionKind
from .digest import derive_clone_digest
from .products import clone_endpoint_fate_spans
from .reaction import derive_clone_end_program

if TYPE_CHECKING:
    from ..realization import MaterializedConstructionRealization


def validate_clone_realization(realization: MaterializedConstructionRealization) -> None:
    """Require exact PCR-spine and clone-ready end-generation replay."""
    item = realization
    validate_pcr_realization(item)
    program = item.construction_program
    basal = item.basal_authority
    if basal is None:
        raise ValueError("Clone-ready routes require one exact basal authority.")
    if (
        len(program.states) < 2
        or tuple(state.phase for state in program.states[-2:])
        != (
            ConstructionStatePhase.HAIRPIN_PCR_DUPLEX,
            ConstructionStatePhase.CLONE_READY_DUPLEX,
        )
        or program.transitions[-1].kind is not ConstructionTransitionKind.END_GENERATION
        or len(program.reaction_programs) != 2
    ):
        raise ValueError("Clone-ready route must append one exact end-generation phase.")
    pcr_state, terminal = program.states[-2:]
    release_program = program.reaction_programs[-1]
    bindings = tuple(
        ConstructionEnzymeBinding.create(
            enzyme_id=operation.enzyme_id,
            role=EnzymeRole.END_GENERATION,
            strand=None,
            recognition_span=operation.intended_binding.recognition_span,
            orientation=operation.intended_binding.orientation,
            reference_cut=operation.intended_binding.reference_cut,
            complement_cut=operation.intended_binding.complement_cut,
        )
        for operation in release_program.stages[0].operations
    )
    if len(bindings) != 2:
        raise ValueError("Clone-ready release requires two exact endpoint bindings.")
    digest = derive_clone_digest(
        bindings=(bindings[0], bindings[1]),
        pcr_state=pcr_state,
        design_sequence=item.design.encoding_sequence,
        design_digest=item.design.encoding_digest,
    )
    expected_program = derive_clone_end_program(pcr_state=pcr_state, digest=digest)
    if program.reaction_programs[-1] != expected_program:
        raise ValueError("Clone end-generation program must replay exact endpoint bindings.")
    if (
        terminal.molecules != digest.strands
        or terminal.pairings != digest.pairings
        or terminal.formed_bonds
    ):
        raise ValueError("Clone terminal state must equal the exact digest molecular graph.")
    product = item.final_product
    reference = product.reference
    if (
        not isinstance(reference, DuplexFinalProductReference)
        or reference.endpoint is not ConstructionEndpoint.CLONE_READY_DUPLEX
        or reference.topology != "linear_duplex"
        or reference.strands != digest.strands
        or reference.pairings != digest.pairings
        or reference.cohesive_ends != digest.cohesive_ends
        or product.strands != digest.strands
        or product.pairings != digest.pairings
        or product.cohesive_ends != digest.cohesive_ends
    ):
        raise ValueError("Clone endpoint must equal its exact staggered duplex graph.")
    if product.encoding_projection != digest.encoding_projection:
        raise ValueError("Clone design authority must equal the exact pre-digest cut union.")
    expected_functions = material_function_spans(
        materials=item.materials,
        top=digest.strands[0],
        bottom=digest.strands[1],
    )
    if product.material_function_spans != expected_functions:
        raise ValueError("Clone material functions must replay exact terminal lineage.")
    expected_fates = clone_endpoint_fate_spans(
        features=item.design.plan.hairpin_encoding_insert.features,
        digest=digest,
    )
    if product.endpoint_sequence_fate_spans != expected_fates:
        raise ValueError("Clone sequence fates must replay both exact digest strands.")


__all__ = ["validate_clone_realization"]
