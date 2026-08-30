"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal/reactions.py

Discovers exact basal construction neighborhoods.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.kernel.construction.basal import (
    BasalProgramCandidate,
    BasalSequenceSolution,
)
from hop_design.models.molecular_replay import strand_from_sequence
from hop_design.models.catalog import ResolvedNickSite
from hop_design.models.construction import (
    BasalTarget,
)
from hop_design.models.construction.basal import (
    BasalEnzymeBinding,
)
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.junction import Strand
from hop_design.models.method_states import MultiSiteNickedDuplex
from hop_design.models.molecular_state import (
    EndChemistry,
    LineageStrand,
    MolecularStrand,
)
from hop_design.models.reactions import (
    DeclaredEnzymeBinding,
    ReactionMolecule,
    ReactionOperation,
    ReactionProgram,
    ReactionStage,
    ReactionState,
)
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.models.strand_state import NickEvent

_ROUTE_VERSION = "linear-source-basal/2"


def _declared(binding: BasalEnzymeBinding) -> DeclaredEnzymeBinding:
    return DeclaredEnzymeBinding(
        recognition_span=binding.recognition_span,
        orientation=binding.orientation,
        reference_cut=binding.reference_cut,
        complement_cut=binding.complement_cut,
    )


def _nick_program(solution: BasalSequenceSolution, route: BasalProgramCandidate) -> ReactionProgram:
    sequence = solution.source_precursor_sequence
    molecule = ReactionMolecule(
        molecule_id="source-precursor",
        reference_sequence_5prime=sequence,
        complement_sequence_5prime=reverse_complement_iupac(sequence),
    )
    binding = solution.enzyme_bindings[0]
    return ReactionProgram(
        program_id="basal-nick-program",
        states=(
            ReactionState(state_id="source-duplex", molecules=(molecule,)),
            ReactionState(state_id="basal-nicked-duplex", molecules=(molecule,)),
        ),
        stages=(
            ReactionStage(
                stage_id="basal-nick",
                pre_state_id="source-duplex",
                post_state_id="basal-nicked-duplex",
                operations=(
                    ReactionOperation(
                        operation_id="basal-nick",
                        enzyme_id=route.nick_enzyme.enzyme_id,
                        role=EnzymeRole.BASAL_NICK,
                        molecule_id=molecule.molecule_id,
                        intended_binding=_declared(binding),
                    ),
                ),
            ),
        ),
    )


def _strand(
    *, strand_id: str, sequence: str, origin_id: str, origin_strand: LineageStrand
) -> MolecularStrand:
    indexes = (
        range(len(sequence))
        if origin_strand is LineageStrand.PRIMARY
        else range(len(sequence) - 1, -1, -1)
    )
    return strand_from_sequence(
        strand_id=strand_id,
        sequence=sequence,
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        origin_id=origin_id,
        origin_strand=origin_strand,
        origin_indexes=indexes,
    )


def _nicked_duplex(solution: BasalSequenceSolution, target: BasalTarget) -> MultiSiteNickedDuplex:
    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Basal reaction realization requires one exact nick strand.")
    sequence = solution.source_precursor_sequence
    binding = solution.enzyme_bindings[0]
    operative = (
        binding.reference_cut if target.nick_strand is Strand.TOP else binding.complement_cut
    )
    if operative is None:
        raise ValueError("basal-nick-cut-unavailable")
    return MultiSiteNickedDuplex(
        top_strand=_strand(
            strand_id="source-top",
            sequence=sequence,
            origin_id="source-precursor",
            origin_strand=LineageStrand.PRIMARY,
        ),
        bottom_strand=_strand(
            strand_id="source-bottom",
            sequence=reverse_complement_iupac(sequence),
            origin_id="source-precursor",
            origin_strand=LineageStrand.COMPLEMENTARY,
        ),
        sites=(
            ResolvedNickSite(
                agent_id=binding.enzyme_id,
                site_span=binding.recognition_span,
                orientation=binding.orientation,
                matched_sequence=sequence[
                    binding.recognition_span.start.offset : binding.recognition_span.end.offset
                ],
                nick=NickEvent(boundary=operative, strand=target.nick_strand),
            ),
        ),
    )
