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
    arm_nt = target.annealing_arm_length_bp
    foldback_nt = target.loop_length_nt + 2 * arm_nt
    source = source_reference_sequence
    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Foldback replay requires one exact nick strand.")
    if target.nick_strand is Strand.TOP:
        junction = payload_nt
        nick = junction + target.nick_offset_within_foldback_nt
        terminus = junction + foldback_nt - target.nick_offset_within_foldback_nt
    else:
        junction = len(source) - payload_nt
        nick = junction - target.nick_offset_within_foldback_nt
        terminus = junction - foldback_nt + target.nick_offset_within_foldback_nt
    nick_binding = next(
        binding for binding in enzyme_bindings if binding.role is EnzymeRole.FOLDBACK_NICK
    )
    foldback_nick = FoldbackBoundaryControl(
        kind=FoldbackTerminusKind.ENZYME_CLEAVAGE,
        strand=target.nick_strand,
        boundary=Boundary(offset=nick),
        end_chemistry=EndChemistry.HYDROXYL,
        enzyme_id=nick_binding.enzyme_id,
        enzyme_class=EnzymeClass.NICKASE,
        binding_id=nick_binding.binding_id,
    )
    if program_kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE:
        if (target.nick_strand is Strand.TOP and len(source) != terminus) or (
            target.nick_strand is Strand.BOTTOM and terminus != 0
        ):
            raise ValueError("A single-cleavage source must physically end at its terminus.")
        source_top_five_prime = (
            EndChemistry.PHOSPHATE if target.nick_strand is Strand.BOTTOM else EndChemistry.HYDROXYL
        )
        source_bottom_five_prime = (
            EndChemistry.PHOSPHATE if target.nick_strand is Strand.TOP else EndChemistry.HYDROXYL
        )
        top_cuts: tuple[int, ...] = (nick,) if target.nick_strand is Strand.TOP else ()
        bottom_cuts: tuple[int, ...] = (nick,) if target.nick_strand is Strand.BOTTOM else ()
        release_cut = DuplexCut(
            top=Boundary(offset=terminus),
            bottom=Boundary(offset=terminus),
        )
        terminus_control = FoldbackBoundaryControl(
            kind=FoldbackTerminusKind.SOURCE_TERMINUS,
            strand=(Strand.BOTTOM if target.nick_strand is Strand.TOP else Strand.TOP),
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
        source_top_five_prime = EndChemistry.HYDROXYL
        source_bottom_five_prime = EndChemistry.HYDROXYL
        top_cuts = (nick, terminus) if target.nick_strand is Strand.TOP else (terminus,)
        bottom_cuts = (terminus,) if target.nick_strand is Strand.TOP else (terminus, nick)
        release_cut = DuplexCut(
            top=terminus_binding.reference_cut,
            bottom=terminus_binding.complement_cut,
        )
        terminus_control = FoldbackBoundaryControl(
            kind=FoldbackTerminusKind.ENZYME_CLEAVAGE,
            strand=(Strand.BOTTOM if target.nick_strand is Strand.TOP else Strand.TOP),
            boundary=Boundary(offset=terminus),
            end_chemistry=EndChemistry.PHOSPHATE,
            enzyme_id=terminus_binding.enzyme_id,
            enzyme_class=EnzymeClass.DUPLEX_RESTRICTION,
            binding_id=terminus_binding.binding_id,
        )

    source_top = _strand(
        strand_id="source-top",
        sequence=source,
        five_prime_end=source_top_five_prime,
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
    if target.nick_strand is Strand.TOP:
        upstream = next(
            fragment
            for fragment in fragments
            if fragment.precursor_strand is Strand.TOP
            and fragment.precursor_span == Span(start=Boundary(offset=0), end=Boundary(offset=nick))
        )
        downstream = next(
            fragment
            for fragment in fragments
            if fragment.precursor_strand is Strand.BOTTOM
            and fragment.precursor_span
            == Span(start=Boundary(offset=0), end=Boundary(offset=terminus))
        )
        route = StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK
        active_span = Span(start=Boundary(offset=0), end=Boundary(offset=terminus))
        active_lineage = range(terminus - 1, -1, -1)
    else:
        upstream = next(
            fragment
            for fragment in fragments
            if fragment.precursor_strand is Strand.BOTTOM
            and fragment.precursor_span
            == Span(start=Boundary(offset=nick), end=Boundary(offset=len(source)))
        )
        downstream = next(
            fragment
            for fragment in fragments
            if fragment.precursor_strand is Strand.TOP
            and fragment.precursor_span
            == Span(start=Boundary(offset=terminus), end=Boundary(offset=len(source)))
        )
        route = StrandExposureRoute.TOP_ACTIVE_AFTER_BOTTOM_NICK
        active_span = Span(start=Boundary(offset=terminus), end=Boundary(offset=len(source)))
        active_lineage = range(terminus, len(source))
    projection = ReleasedStrandState(
        route=route,
        precursor_top_strand=source,
        active_strand=downstream.precursor_strand,
        retained_partner_strand=upstream.precursor_strand,
        nick=NickEvent(boundary=Boundary(offset=nick), strand=target.nick_strand),
        release_cut=release_cut,
        active_product_precursor_span=active_span,
        active_nick_boundary=Boundary(
            offset=(terminus - nick if target.nick_strand is Strand.TOP else nick - terminus)
        ),
        active_product_sequence=downstream.sequence,
        retained_partner_sequence=upstream.sequence,
        active_product_lineage=tuple(
            BaseLineage(
                active_index=index,
                precursor_strand=downstream.precursor_strand,
                precursor_index=precursor_index,
            )
            for index, precursor_index in enumerate(active_lineage)
        ),
    )

    if upstream.three_prime_end is not EndChemistry.HYDROXYL:
        raise ValueError("Foldback ligation requires a three-prime hydroxyl.")
    if downstream.five_prime_end is not EndChemistry.PHOSPHATE:
        raise ValueError("Foldback ligation requires a five-prime phosphate.")
    bond = CovalentBond(
        upstream_strand_id=upstream.fragment_id,
        upstream_end=StrandEnd.THREE_PRIME,
        downstream_strand_id=downstream.fragment_id,
        downstream_end=StrandEnd.FIVE_PRIME,
    )
    ligated = MolecularStrand(
        strand_id="ligated-foldback-strand",
        sequence=upstream.sequence + downstream.sequence,
        five_prime_end=upstream.five_prime_end,
        three_prime_end=downstream.three_prime_end,
        lineage=_reindex_lineage((upstream.lineage, downstream.lineage)),
    )
    foldback = ligated.sequence[payload_nt : payload_nt + foldback_nt]
    retained_arm = foldback[:arm_nt]
    loop_start = arm_nt
    loop_end = loop_start + target.loop_length_nt
    loop = foldback[loop_start:loop_end]
    arm_start = loop_end
    arm_end = arm_start + arm_nt
    arm = foldback[arm_start:arm_end]
    expected_arm = reverse_complement_iupac(retained_arm)
    if arm != expected_arm:
        raise ValueError("Released foldback arms must be literally complementary.")
    pairs = tuple(
        StrandPairObservation(
            left_strand_id=(
                upstream.fragment_id
                if index < target.nick_offset_within_foldback_nt
                else downstream.fragment_id
            ),
            right_strand_id=downstream.fragment_id,
            left_index=(
                payload_nt + index
                if index < target.nick_offset_within_foldback_nt
                else index - target.nick_offset_within_foldback_nt
            ),
            right_index=(arm_end - 1 - index - target.nick_offset_within_foldback_nt),
            left_base=retained_arm[index],
            right_base=arm[arm_nt - 1 - index],
            kind=classify_literal_pair(
                left_base=retained_arm[index],
                right_base=arm[arm_nt - 1 - index],
            ),
        )
        for index in range(arm_nt)
    )
    program = _reaction_program(
        source=source,
        program_kind=program_kind,
        junction=nick,
        terminus=terminus,
        bindings=enzyme_bindings,
        fragments=fragments,
    )
    retained_ids = {upstream.fragment_id, downstream.fragment_id}
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
