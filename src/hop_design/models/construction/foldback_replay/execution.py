"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/foldback_replay/execution.py

Replays foldback cleavage, release, annealing, and ligation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import FoldbackTarget
from hop_design.models.construction.foldback import (
    FoldbackBoundaryControl,
    FoldbackCleavageProgramKind,
    FoldbackEnzymeBinding,
    FoldbackTerminusKind,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport
from hop_design.models.enzymes import EnzymeClass, EnzymeRole
from hop_design.models.molecular_state import (
    CovalentBond,
    EndChemistry,
    LineageStrand,
    MolecularStrand,
    StrandEnd,
    StrandPairObservation,
)
from hop_design.models.physical import Strand, classify_literal_pair
from hop_design.models.reactions import (
    ActionableEnzymeBinding,
    ReactionProgram,
    ReactionStageAssessment,
)
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.models.strand_state import (
    BaseLineage,
    DuplexCut,
    NickEvent,
    ReleasedStrandState,
    StrandExposureRoute,
)

from .states import FoldbackRouteReplay, _fragments, _reaction_program, _reindex_lineage, _strand


def _accepted_stage_assessments(
    program: ReactionProgram,
) -> tuple[ReactionStageAssessment, ...]:
    return tuple(
        ReactionStageAssessment(
            stage_id=stage.stage_id,
            resolved_against_state_id=stage.pre_state_id,
            intended_bindings=tuple(
                ActionableEnzymeBinding(
                    enzyme_id=operation.enzyme_id,
                    molecule_id=operation.molecule_id,
                    recognition_span=operation.intended_binding.recognition_span,
                    orientation=operation.intended_binding.orientation,
                    reference_cut=operation.intended_binding.reference_cut,
                    complement_cut=operation.intended_binding.complement_cut,
                    operation_id=operation.operation_id,
                )
                for operation in stage.operations
            ),
            undeclared_bindings=(),
            report=CheckReport(),
        )
        for stage in program.stages
    )


def replay_foldback_route(
    *,
    payload_sequence: str,
    target: FoldbackTarget,
    program_kind: FoldbackCleavageProgramKind,
    source_reference_sequence: str,
    enzyme_bindings: tuple[FoldbackEnzymeBinding, ...],
) -> FoldbackRouteReplay:
    """Derive every physical foldback state from exact source and cut authorities."""
    payload_nt = len(payload_sequence)
    junction = payload_nt + target.junction_offset_nt
    arm_nt = target.annealing_arm_length_bp
    terminus = junction + target.loop_length_nt + 2 * arm_nt
    source = source_reference_sequence
    nick_binding = next(
        binding for binding in enzyme_bindings if binding.role is EnzymeRole.FOLDBACK_NICK
    )
    foldback_nick = FoldbackBoundaryControl(
        kind=FoldbackTerminusKind.ENZYME_CLEAVAGE,
        strand=Strand.TOP,
        boundary=Boundary(offset=junction),
        end_chemistry=EndChemistry.HYDROXYL,
        enzyme_id=nick_binding.enzyme_id,
        enzyme_class=EnzymeClass.NICKASE,
        binding_id=nick_binding.binding_id,
    )
    if program_kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE:
        if len(source) != terminus:
            raise ValueError("A single-cleavage source must physically end at its terminus.")
        source_bottom_five_prime = EndChemistry.PHOSPHATE
        top_cuts: tuple[int, ...] = (junction,)
        bottom_cuts: tuple[int, ...] = ()
        release_cut = DuplexCut(
            top=Boundary(offset=terminus),
            bottom=Boundary(offset=terminus),
        )
        terminus_control = FoldbackBoundaryControl(
            kind=FoldbackTerminusKind.SOURCE_TERMINUS,
            strand=Strand.BOTTOM,
            boundary=Boundary(offset=terminus),
            end_chemistry=EndChemistry.PHOSPHATE,
        )
    else:
        terminus_binding = next(
            binding for binding in enzyme_bindings if binding.role is EnzymeRole.TERMINUS_DEFINITION
        )
        if terminus_binding.reference_cut != Boundary(
            offset=terminus
        ) or terminus_binding.complement_cut != Boundary(offset=terminus):
            raise ValueError("The current foldback replay requires a blunt terminus cut.")
        source_bottom_five_prime = EndChemistry.HYDROXYL
        top_cuts = (junction, terminus)
        bottom_cuts = (terminus,)
        release_cut = DuplexCut(
            top=terminus_binding.reference_cut,
            bottom=terminus_binding.complement_cut,
        )
        terminus_control = FoldbackBoundaryControl(
            kind=FoldbackTerminusKind.ENZYME_CLEAVAGE,
            strand=Strand.BOTTOM,
            boundary=Boundary(offset=terminus),
            end_chemistry=EndChemistry.PHOSPHATE,
            enzyme_id=terminus_binding.enzyme_id,
            enzyme_class=EnzymeClass.DUPLEX_RESTRICTION,
            binding_id=terminus_binding.binding_id,
        )

    source_top = _strand(
        strand_id="source-top",
        sequence=source,
        five_prime_end=EndChemistry.HYDROXYL,
        origin_strand=LineageStrand.PRIMARY,
        origin_indexes=range(len(source)),
    )
    source_bottom = _strand(
        strand_id="source-bottom",
        sequence=reverse_complement_iupac(source),
        five_prime_end=source_bottom_five_prime,
        origin_strand=LineageStrand.COMPLEMENTARY,
        origin_indexes=range(len(source) - 1, -1, -1),
    )
    fragments = _fragments(
        source=source,
        top_cuts=top_cuts,
        bottom_cuts=bottom_cuts,
        top_five_prime_end=source_top.five_prime_end,
        bottom_five_prime_end=source_bottom.five_prime_end,
    )
    top = next(
        fragment
        for fragment in fragments
        if fragment.precursor_strand is Strand.TOP
        and fragment.precursor_span
        == Span(
            start=Boundary(offset=0),
            end=Boundary(offset=junction),
        )
    )
    bottom = next(
        fragment
        for fragment in fragments
        if fragment.precursor_strand is Strand.BOTTOM
        and fragment.precursor_span
        == Span(
            start=Boundary(offset=0),
            end=Boundary(offset=terminus),
        )
    )
    projection = ReleasedStrandState(
        route=StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
        precursor_top_strand=source,
        active_strand=Strand.BOTTOM,
        retained_partner_strand=Strand.TOP,
        nick=NickEvent(boundary=Boundary(offset=junction), strand=Strand.TOP),
        release_cut=release_cut,
        active_product_precursor_span=Span(
            start=Boundary(offset=0),
            end=Boundary(offset=terminus),
        ),
        active_nick_boundary=Boundary(offset=terminus - junction),
        active_product_sequence=bottom.sequence,
        retained_partner_sequence=top.sequence,
        active_product_lineage=tuple(
            BaseLineage(
                active_index=index,
                precursor_strand=Strand.BOTTOM,
                precursor_index=precursor_index,
            )
            for index, precursor_index in enumerate(range(terminus - 1, -1, -1))
        ),
    )

    retained_arm = bottom.sequence[:arm_nt]
    loop_start = arm_nt
    loop_end = loop_start + target.loop_length_nt
    loop = bottom.sequence[loop_start:loop_end]
    arm_start = loop_end
    arm_end = arm_start + arm_nt
    arm = bottom.sequence[arm_start:arm_end]
    expected_arm = reverse_complement_iupac(retained_arm)
    if arm != expected_arm:
        raise ValueError("Released foldback arms must be literally complementary.")
    pairs = tuple(
        StrandPairObservation(
            left_strand_id=bottom.fragment_id,
            right_strand_id=bottom.fragment_id,
            left_index=index,
            right_index=arm_end - 1 - index,
            left_base=retained_arm[index],
            right_base=arm[arm_nt - 1 - index],
            kind=classify_literal_pair(
                left_base=retained_arm[index],
                right_base=arm[arm_nt - 1 - index],
            ),
        )
        for index in range(arm_nt)
    )
    if top.three_prime_end is not EndChemistry.HYDROXYL:
        raise ValueError("Foldback ligation requires a three-prime hydroxyl.")
    if bottom.five_prime_end is not EndChemistry.PHOSPHATE:
        raise ValueError("Foldback ligation requires a five-prime phosphate.")
    bond = CovalentBond(
        upstream_strand_id=top.fragment_id,
        upstream_end=StrandEnd.THREE_PRIME,
        downstream_strand_id=bottom.fragment_id,
        downstream_end=StrandEnd.FIVE_PRIME,
    )
    ligated = MolecularStrand(
        strand_id="ligated-foldback-strand",
        sequence=top.sequence + bottom.sequence,
        five_prime_end=top.five_prime_end,
        three_prime_end=bottom.three_prime_end,
        lineage=_reindex_lineage((top.lineage, bottom.lineage)),
    )
    program = _reaction_program(
        source=source,
        program_kind=program_kind,
        junction=junction,
        terminus=terminus,
        bindings=enzyme_bindings,
        fragments=fragments,
    )
    retained_ids = {top.fragment_id, bottom.fragment_id}
    return FoldbackRouteReplay(
        source_top_strand=source_top,
        source_bottom_strand=source_bottom,
        foldback_nick=foldback_nick,
        terminus=terminus_control,
        reaction_program=program,
        stage_assessments=_accepted_stage_assessments(program),
        molecular_fragments=fragments,
        released_fragment_ids=tuple(
            fragment.fragment_id
            for fragment in fragments
            if fragment.fragment_id not in retained_ids
        ),
        released_state=projection,
        annealing_pairs=pairs,
        ligation_bond=bond,
        ligated_strand=ligated,
        loop_sequence=loop,
        foldback_arm_sequence=arm,
    )
