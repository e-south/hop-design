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
    BasalPairAllowance,
    BasalTarget,
    ConstructionEndpoint,
    NickStrandSelection,
)
from hop_design.models.construction.basal import (
    BasalPairingProfile,
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
)
from hop_design.models.junction import Strand
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

_BASES = ("A", "C", "G", "T")


@dataclass(frozen=True, slots=True)
class BasalProgramCandidate:
    """One oriented basal nick program."""

    nick_enzyme: CharacterizedEnzyme
    nick_orientation: SiteOrientation


@dataclass(frozen=True, slots=True)
class BasalSequenceSolution:
    """One exact precursor, adapter, pairing profile, and binding set."""

    source_precursor_sequence: str
    adapter_sequence: str | None
    payload_span: Span
    pairing_profile: BasalPairingProfile | None
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
    if endpoint is not ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        raise ValueError("Basal local discovery requires the hairpin PCR intermediate.")
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
            programs.append(BasalProgramCandidate(nickase, nick_orientation))
    return tuple(programs)


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
