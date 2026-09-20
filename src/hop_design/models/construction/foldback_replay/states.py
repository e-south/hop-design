"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/foldback_replay/states.py

Replays foldback cleavage, release, annealing, and ligation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from hop_design.models.construction.foldback import (
    FoldbackBoundaryControl,
    FoldbackCleavageProgramKind,
    FoldbackEnzymeBinding,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.molecular_state import (
    CovalentBond,
    EndChemistry,
    Fragment,
    LineageDirection,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
    StrandPairObservation,
)
from hop_design.models.physical import Strand
from hop_design.models.reactions import (
    DeclaredEnzymeBinding,
    ReactionMolecule,
    ReactionOperation,
    ReactionProgram,
    ReactionStage,
    ReactionStageAssessment,
    ReactionState,
)
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.models.strand_state import (
    ReleasedStrandState,
)

from .substrates import FoldbackReactionSubstrate, foldback_reaction_substrates


@dataclass(frozen=True, slots=True)
class FoldbackRouteReplay:
    """Exact molecular authorities derived from one foldback source and cut program."""

    source_top_strand: MolecularStrand
    source_bottom_strand: MolecularStrand
    foldback_nick: FoldbackBoundaryControl
    terminus: FoldbackBoundaryControl
    reaction_program: ReactionProgram
    stage_assessments: tuple[ReactionStageAssessment, ...]
    molecular_fragments: tuple[Fragment, ...]
    released_fragment_ids: tuple[str, ...]
    released_state: ReleasedStrandState
    annealing_pairs: tuple[StrandPairObservation, ...]
    ligation_bond: CovalentBond
    ligated_strand: MolecularStrand
    loop_sequence: str
    foldback_arm_sequence: str


def _lineage(
    *,
    origin_strand: LineageStrand,
    origin_indexes: range,
) -> tuple[MaterialBaseLineage, ...]:
    return tuple(
        MaterialBaseLineage(
            product_index=product_index,
            origin_id="linear-source",
            origin_strand=origin_strand,
            origin_index=origin_index,
        )
        for product_index, origin_index in enumerate(origin_indexes)
    )


def _strand(
    *,
    strand_id: str,
    sequence: str,
    five_prime_end: EndChemistry,
    origin_strand: LineageStrand,
    origin_indexes: range,
) -> MolecularStrand:
    return MolecularStrand(
        strand_id=strand_id,
        sequence=sequence,
        five_prime_end=five_prime_end,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=_lineage(
            origin_strand=origin_strand,
            origin_indexes=origin_indexes,
        ),
    )


def _fragments(
    *,
    source: str,
    top_cuts: tuple[int, ...],
    bottom_cuts: tuple[int, ...],
    top_five_prime_end: EndChemistry,
    bottom_five_prime_end: EndChemistry,
) -> tuple[Fragment, ...]:
    length = len(source)
    records: list[Fragment] = []
    for start, end in pairwise((0, *top_cuts, length)):
        records.append(
            Fragment(
                fragment_id=f"top-{start}-{end}",
                precursor_strand=Strand.TOP,
                precursor_span=Span(
                    start=Boundary(offset=start),
                    end=Boundary(offset=end),
                ),
                lineage_direction=LineageDirection.FORWARD,
                sequence=source[start:end],
                five_prime_end=(top_five_prime_end if start == 0 else EndChemistry.PHOSPHATE),
                three_prime_end=EndChemistry.HYDROXYL,
                lineage=_lineage(
                    origin_strand=LineageStrand.PRIMARY,
                    origin_indexes=range(start, end),
                ),
            )
        )
    for start, end in tuple(pairwise((0, *bottom_cuts, length)))[::-1]:
        records.append(
            Fragment(
                fragment_id=f"bottom-{start}-{end}",
                precursor_strand=Strand.BOTTOM,
                precursor_span=Span(
                    start=Boundary(offset=start),
                    end=Boundary(offset=end),
                ),
                lineage_direction=LineageDirection.REVERSE,
                sequence=reverse_complement_iupac(source[start:end]),
                five_prime_end=(bottom_five_prime_end if end == length else EndChemistry.PHOSPHATE),
                three_prime_end=EndChemistry.HYDROXYL,
                lineage=_lineage(
                    origin_strand=LineageStrand.COMPLEMENTARY,
                    origin_indexes=range(end - 1, start - 1, -1),
                ),
            )
        )
    return tuple(records)


def _reindex_lineage(
    groups: tuple[tuple[MaterialBaseLineage, ...], ...],
) -> tuple[MaterialBaseLineage, ...]:
    records: list[MaterialBaseLineage] = []
    for group in groups:
        for item in group:
            records.append(item.model_copy(update={"product_index": len(records)}))
    return tuple(records)


def _declared_binding(binding: FoldbackEnzymeBinding) -> DeclaredEnzymeBinding:
    return DeclaredEnzymeBinding(
        recognition_span=binding.recognition_span,
        orientation=binding.orientation,
        reference_cut=binding.reference_cut,
        complement_cut=binding.complement_cut,
    )


def _shifted_declared_binding(
    binding: FoldbackEnzymeBinding, *, offset: int
) -> DeclaredEnzymeBinding:
    return DeclaredEnzymeBinding(
        recognition_span=Span(
            start=Boundary(offset=binding.recognition_span.start.offset - offset),
            end=Boundary(offset=binding.recognition_span.end.offset - offset),
        ),
        orientation=binding.orientation,
        reference_cut=(
            Boundary(offset=binding.reference_cut.offset - offset)
            if binding.reference_cut is not None
            else None
        ),
        complement_cut=(
            Boundary(offset=binding.complement_cut.offset - offset)
            if binding.complement_cut is not None
            else None
        ),
    )


def _substrate_state(
    *, source: str, state_id: str, substrates: tuple[FoldbackReactionSubstrate, ...]
) -> ReactionState:
    return ReactionState(
        state_id=state_id,
        molecules=tuple(
            ReactionMolecule(
                molecule_id=substrate.molecule_id,
                reference_sequence_5prime=sequence,
                complement_sequence_5prime=reverse_complement_iupac(sequence),
            )
            for substrate in substrates
            if substrate.state_id == state_id
            for sequence in (
                source[substrate.source_span.start.offset : substrate.source_span.end.offset],
            )
        ),
    )


def _reaction_program(
    *,
    source: str,
    program_kind: FoldbackCleavageProgramKind,
    junction: int,
    terminus: int,
    bindings: tuple[FoldbackEnzymeBinding, ...],
    fragments: tuple[Fragment, ...],
) -> ReactionProgram:
    nick_binding = next(binding for binding in bindings if binding.role is EnzymeRole.FOLDBACK_NICK)
    substrates = foldback_reaction_substrates(
        source_nt=len(source),
        program_kind=program_kind,
        nick_strand=nick_binding.strand,
        terminus=terminus,
    )
    source_state = _substrate_state(source=source, state_id="source-duplex", substrates=substrates)
    released_state = ReactionState(
        state_id="released-foldback-strands",
        molecules=tuple(
            ReactionMolecule(
                molecule_id=fragment.fragment_id,
                reference_sequence_5prime=fragment.sequence,
                complement_sequence_5prime=None,
            )
            for fragment in fragments
        ),
    )
    nick_operation = ReactionOperation(
        operation_id="foldback-nick",
        enzyme_id=nick_binding.enzyme_id,
        role=EnzymeRole.FOLDBACK_NICK,
        molecule_id="source",
        intended_binding=_declared_binding(nick_binding),
    )
    if program_kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE:
        return ReactionProgram(
            program_id="foldback-single-cleavage",
            states=(source_state, released_state),
            stages=(
                ReactionStage(
                    stage_id="foldback-nick",
                    pre_state_id=source_state.state_id,
                    post_state_id=released_state.state_id,
                    operations=(nick_operation,),
                ),
            ),
        )

    terminus_binding = next(
        binding for binding in bindings if binding.role is EnzymeRole.TERMINUS_DEFINITION
    )
    intermediate_state = _substrate_state(
        source=source, state_id="terminus-defined-duplexes", substrates=substrates
    )
    terminus_operation = ReactionOperation(
        operation_id="terminus-definition",
        enzyme_id=terminus_binding.enzyme_id,
        role=EnzymeRole.TERMINUS_DEFINITION,
        molecule_id="source",
        intended_binding=_declared_binding(terminus_binding),
    )
    retained_offset = next(
        substrate.source_span.start.offset
        for substrate in substrates
        if substrate.state_id == intermediate_state.state_id and substrate.molecule_id == "source"
    )
    if retained_offset:
        nick_operation = nick_operation.model_copy(
            update={
                "intended_binding": _shifted_declared_binding(
                    nick_binding,
                    offset=retained_offset,
                )
            }
        )
    return ReactionProgram(
        program_id="foldback-sequential-cleavage",
        states=(source_state, intermediate_state, released_state),
        stages=(
            ReactionStage(
                stage_id="terminus-definition",
                pre_state_id=source_state.state_id,
                post_state_id=intermediate_state.state_id,
                operations=(terminus_operation,),
            ),
            ReactionStage(
                stage_id="foldback-nick",
                pre_state_id=intermediate_state.state_id,
                post_state_id=released_state.state_id,
                operations=(nick_operation,),
            ),
        ),
    )
