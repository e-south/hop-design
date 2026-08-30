"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/clone/reaction.py

Derives the exact concurrent Type IIS reaction program for a clone-ready endpoint.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalEnzymeBinding, BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.construction.payload import _content_id
from hop_design.models.coordinates import Span
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.reactions import (
    DeclaredEnzymeBinding,
    ReactionMolecule,
    ReactionOperation,
    ReactionProgram,
    ReactionStage,
    ReactionState,
)
from hop_design.models.sequence import reverse_complement_iupac

from ..state import ConstructionState
from .digest import CloneDigest
from .geometry import (
    CloneEndGenerationError,
    derive_clone_cut_geometry,
    lift_clone_end_bindings,
    validate_clone_binding_definitions,
)


def _declared(binding: BasalEnzymeBinding) -> DeclaredEnzymeBinding:
    return DeclaredEnzymeBinding(
        recognition_span=binding.recognition_span,
        orientation=binding.orientation,
        reference_cut=binding.reference_cut,
        complement_cut=binding.complement_cut,
    )


def derive_clone_end_program(
    *,
    pcr_state: ConstructionState,
    digest: CloneDigest,
) -> ReactionProgram:
    """Derive one concurrent Type IIS program from exact complete-route facts."""
    top, _ = pcr_state.molecules
    program, projection = derive_clone_end_program_for_template(
        basal=None,
        foldback=None,
        pcr_top=top.sequence,
        bindings=digest.bindings,
        design_sequence=digest.encoding_projection.sequence,
    )
    if projection != digest.encoding_projection.source_span:
        raise CloneEndGenerationError("Clone program must preserve the exact design union.")
    expected_post = tuple(item.reference_sequence_5prime for item in program.states[-1].molecules)
    if expected_post != tuple(strand.sequence for strand in digest.strands):
        raise CloneEndGenerationError("Clone program must preserve exact digest products.")
    return program


def derive_clone_end_program_for_template(
    *,
    basal: BasalRealizationRecord | None,
    foldback: FoldbackLocalRealization | None,
    pcr_top: str,
    design_sequence: str,
    bindings: tuple[BasalEnzymeBinding, BasalEnzymeBinding] | None = None,
) -> tuple[ReactionProgram, Span]:
    """Derive exact end-generation reaction bytes from one complete PCR template."""
    if bindings is None:
        if basal is None or foldback is None:
            raise CloneEndGenerationError(
                "Clone end generation requires local authorities or lifted bindings."
            )
        bindings = lift_clone_end_bindings(basal=basal, foldback=foldback)
    validate_clone_binding_definitions(bindings=bindings, basal=basal, sequence=pcr_top)
    geometry = derive_clone_cut_geometry(
        bindings=bindings,
        parent_length=len(pcr_top),
        template_sequence=pcr_top,
        design_sequence=design_sequence,
    )
    pcr_bottom = reverse_complement_iupac(pcr_top)
    primary_sequence = pcr_top[
        geometry.primary_parent_span.start.offset : geometry.primary_parent_span.end.offset
    ]
    complementary_start = geometry.complementary_parent_span.start.offset
    complementary_end = geometry.complementary_parent_span.end.offset
    complementary_sequence = pcr_bottom[complementary_start:complementary_end]
    pre = ReactionState(
        state_id="complete-hairpin-pcr-duplex",
        molecules=(
            ReactionMolecule(
                molecule_id="complete-hairpin-pcr",
                reference_sequence_5prime=pcr_top,
                complement_sequence_5prime=pcr_bottom,
            ),
        ),
    )
    post = ReactionState(
        state_id="complete-clone-ready-duplex",
        molecules=(
            ReactionMolecule(
                molecule_id="complete-clone-primary",
                reference_sequence_5prime=primary_sequence,
                complement_sequence_5prime=None,
            ),
            ReactionMolecule(
                molecule_id="complete-clone-complementary",
                reference_sequence_5prime=complementary_sequence,
                complement_sequence_5prime=None,
            ),
        ),
    )
    operations = tuple(
        ReactionOperation(
            operation_id=f"complete-end-generation-{side}",
            enzyme_id=binding.enzyme_id,
            role=EnzymeRole.END_GENERATION,
            molecule_id="complete-hairpin-pcr",
            intended_binding=_declared(binding),
        )
        for side, binding in zip(("left", "right"), bindings, strict=True)
    )
    identity = (
        _content_id(
            "clone-end-generation",
            1,
            {
                "pre": pre.model_dump(mode="json"),
                "post": post.model_dump(mode="json"),
                "operations": tuple(item.model_dump(mode="json") for item in operations),
            },
        )
        .split("/")[-1]
        .split("@")[0]
    )
    stage = ReactionStage(
        stage_id=f"clone-end-generation-{identity}",
        pre_state_id=pre.state_id,
        post_state_id=post.state_id,
        operations=operations,
    )
    return (
        ReactionProgram(
            program_id=f"clone-end-generation-{identity}",
            states=(pre, post),
            stages=(stage,),
        ),
        geometry.encoding_span,
    )


__all__ = ["derive_clone_end_program", "derive_clone_end_program_for_template"]
