"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/basal/programs.py

Enumerates exact basal construction programs and sequence solutions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction import (
    BasalFutureReleaseAction,
    BasalFutureReleaseRequirement,
    BasalPairAllowance,
    BasalTarget,
    ConstructionEndpoint,
    NickStrandSelection,
)
from hop_design.models.construction.basal import (
    BasalPairingState,
    derive_basal_pair_class,
)
from hop_design.models.construction.enzyme_binding import ConstructionEnzymeBinding
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    EnzymeClass,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    RecognitionOrientationSemantics,
    characterized_enzyme_digest,
)
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import StrandEnd
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

_BASES = ("A", "C", "G", "T")


@dataclass(frozen=True, slots=True)
class BasalProgramCandidate:
    """One oriented basal nick with any required future release action."""

    nick_enzyme: CharacterizedEnzyme
    nick_orientation: SiteOrientation
    future_release_enzyme: CharacterizedEnzyme | None = None
    future_release_action: BasalFutureReleaseAction | None = None


@dataclass(frozen=True, slots=True)
class BasalSequenceSolution:
    """One exact precursor, adapter, pairing state, and binding set."""

    source_precursor_sequence: str
    adapter_sequence: str | None
    payload_span: Span
    pairing_state: BasalPairingState | None
    enzyme_bindings: tuple[ConstructionEnzymeBinding, ...]


@dataclass(frozen=True, slots=True)
class BasalPlacementFailure:
    """One stable incompatibility discovered before a molecular trajectory exists."""

    code: str


def _orientations(enzyme: CharacterizedEnzyme) -> tuple[SiteOrientation, ...]:
    if (
        enzyme.recognition_orientation_semantics
        is RecognitionOrientationSemantics.BOTH_ORIENTATIONS
    ):
        return (SiteOrientation.FORWARD, SiteOrientation.REVERSE)
    return (SiteOrientation.FORWARD,)


def _oriented_pattern(enzyme: CharacterizedEnzyme, orientation: SiteOrientation) -> str:
    return (
        enzyme.recognition_pattern
        if orientation is SiteOrientation.FORWARD
        else reverse_complement_iupac(enzyme.recognition_pattern)
    )


def _oriented_cuts(
    enzyme: CharacterizedEnzyme, *, orientation: SiteOrientation, site_start: int
) -> tuple[int | None, int | None]:
    if orientation is SiteOrientation.FORWARD:
        reference_offset = enzyme.cut_offset_reference_strand
        complement_offset = enzyme.cut_offset_complement_strand
    elif enzyme.enzyme_class is EnzymeClass.NICKASE:
        reference_offset = None
        complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
    else:
        if enzyme.cut_offset_complement_strand is None:
            raise ValueError("Duplex restriction enzymes require two cut offsets.")
        reference_offset = enzyme.recognition_length - enzyme.cut_offset_complement_strand
        complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
    return (
        site_start + reference_offset if reference_offset is not None else None,
        site_start + complement_offset if complement_offset is not None else None,
    )


def iter_basal_programs(
    policy: EnzymeProvisioningPolicy, *, target: BasalTarget, endpoint: ConstructionEndpoint
) -> tuple[BasalProgramCandidate, ...]:
    """Enumerate every provisioned oriented program in canonical order."""
    programs: list[BasalProgramCandidate] = []
    nickases = tuple(
        enzyme
        for enzyme in sorted(policy.catalog.enzymes, key=lambda item: item.enzyme_id)
        if enzyme.enzyme_class is EnzymeClass.NICKASE
        and policy.permits(enzyme.enzyme_id, role=EnzymeRole.BASAL_NICK)
    )
    if endpoint not in {
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    }:
        raise ValueError("Basal local discovery requires a PCR-bearing endpoint.")
    release_actions: tuple[
        tuple[CharacterizedEnzyme, BasalFutureReleaseAction] | tuple[None, None], ...
    ]
    if endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        if target.future_release is not None:
            raise ValueError("A hairpin PCR basal target must omit future end generation.")
        release_actions = ((None, None),)
    else:
        if target.future_release is None:
            raise ValueError("A clone-ready basal target requires future end generation.")
        release_actions = tuple(
            (enzyme, action)
            for enzyme in sorted(policy.catalog.enzymes, key=lambda item: item.enzyme_id)
            if policy.permits(enzyme.enzyme_id, role=EnzymeRole.END_GENERATION)
            for action in (_future_release_action(enzyme, target.future_release),)
            if action is not None
        )
    for nickase in nickases:
        for nick_orientation in _orientations(nickase):
            controlled = (
                Strand.TOP if nick_orientation is SiteOrientation.FORWARD else Strand.BOTTOM
            )
            if (
                target.nick_strand is not NickStrandSelection.ANY
                and controlled is not target.nick_strand
            ):
                continue
            programs.extend(
                BasalProgramCandidate(
                    nick_enzyme=nickase,
                    nick_orientation=nick_orientation,
                    future_release_enzyme=release_enzyme,
                    future_release_action=release_action,
                )
                for release_enzyme, release_action in release_actions
            )
    return tuple(programs)


def _future_release_action(
    enzyme: CharacterizedEnzyme,
    requirement: BasalFutureReleaseRequirement,
) -> BasalFutureReleaseAction | None:
    """Resolve one future Type IIS action without asserting a current physical end."""
    if (
        enzyme.enzyme_class is not EnzymeClass.DUPLEX_RESTRICTION
        or enzyme.cut_offset_complement_strand is None
        or requirement.orientation not in _orientations(enzyme)
    ):
        return None
    if requirement.orientation is SiteOrientation.FORWARD:
        reference_offset = enzyme.cut_offset_reference_strand
        complement_offset = enzyme.cut_offset_complement_strand
    else:
        reference_offset = enzyme.recognition_length - enzyme.cut_offset_complement_strand
        complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
    if not (
        (
            reference_offset >= enzyme.recognition_length
            and complement_offset >= enzyme.recognition_length
        )
        or (reference_offset <= 0 and complement_offset <= 0)
    ):
        return None
    if abs(reference_offset - complement_offset) != len(requirement.cohesive_end_sequence):
        return None
    expected_end = (
        StrandEnd.FIVE_PRIME if reference_offset < complement_offset else StrandEnd.THREE_PRIME
    )
    if requirement.overhang_end is not expected_end:
        return None
    boundary_shift = (
        -min(reference_offset, complement_offset)
        if requirement.product_end == "left"
        else -max(reference_offset, complement_offset)
    )
    return BasalFutureReleaseAction.create(
        enzyme_id=enzyme.enzyme_id,
        enzyme_digest=characterized_enzyme_digest(enzyme),
        requirement=requirement,
        recognition_pattern_5prime=_oriented_pattern(enzyme, requirement.orientation),
        recognition_start_from_release_boundary=boundary_shift,
        reference_cut_from_release_boundary=boundary_shift + reference_offset,
        complement_cut_from_release_boundary=boundary_shift + complement_offset,
    )


def _constrain(domains: list[set[str]], *, start: int, pattern: str) -> bool:
    for index, symbol in enumerate(pattern):
        domains[start + index] &= set(iupac_bases(symbol))
        if not domains[start + index]:
            return False
    return True


def _adapter_domains(source_base: str, allowance: BasalPairAllowance) -> tuple[str, ...]:
    return tuple(
        base
        for base in _BASES
        if allowance is BasalPairAllowance.ANY
        or derive_basal_pair_class(source_base, base).value == allowance.value
    )


def _binding(
    *,
    enzyme: CharacterizedEnzyme,
    role: EnzymeRole,
    strand: Strand | None,
    orientation: SiteOrientation,
    start: int,
) -> ConstructionEnzymeBinding:
    reference, complement = _oriented_cuts(enzyme, orientation=orientation, site_start=start)
    return ConstructionEnzymeBinding.create(
        enzyme_id=enzyme.enzyme_id,
        role=role,
        strand=strand,
        recognition_span=Span(
            start=Boundary(offset=start), end=Boundary(offset=start + enzyme.recognition_length)
        ),
        orientation=orientation,
        reference_cut=Boundary(offset=reference) if reference is not None else None,
        complement_cut=Boundary(offset=complement) if complement is not None else None,
    )
