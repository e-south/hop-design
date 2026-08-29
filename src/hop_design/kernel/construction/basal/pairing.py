"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/basal/pairing.py

Enumerates exact basal construction programs and sequence solutions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from hop_design.models.construction import (
    BasalPairClass,
)
from hop_design.models.construction.basal import (
    BasalEnzymeBinding,
    BasalPairingProfile,
    BasalPairRecord,
    derive_basal_pair_class,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.molecular_state import CohesiveEnd, StrandEnd
from hop_design.models.sequence import normalize_dna_sequence, reverse_complement_iupac


def _compact_symbol(pair_class: BasalPairClass) -> Literal["M", "W", "X"]:
    if pair_class is BasalPairClass.MATCH:
        return "M"
    if pair_class is BasalPairClass.WOBBLE:
        return "W"
    return "X"


def resolve_basal_pairing_profile(
    *,
    source_sequence_5prime: str,
    adapter_sequence_5prime: str,
    source_span: Span | None = None,
    adapter_span: Span | None = None,
    end_projection_positions: tuple[int, ...] = (),
) -> BasalPairingProfile:
    """Classify exact antiparallel pairs from the payload outward."""
    source = normalize_dna_sequence(source_sequence_5prime, allow_degenerate=False)
    adapter = normalize_dna_sequence(adapter_sequence_5prime, allow_degenerate=False)
    if not source or len(source) != len(adapter):
        raise ValueError("Basal source and adapter arms must have equal nonzero length.")
    if len(end_projection_positions) != len(set(end_projection_positions)) or any(
        position < 0 or position >= len(source) for position in end_projection_positions
    ):
        raise ValueError("End-projection positions must be unique basal profile indexes.")
    pairs = []
    for position in range(len(source)):
        source_index = len(source) - 1 - position
        source_base = source[source_index]
        adapter_base = adapter[position]
        pair_class = derive_basal_pair_class(source_base, adapter_base)
        pairs.append(
            BasalPairRecord(
                profile_position=position,
                source_index=source_index,
                adapter_index=position,
                source_base=source_base,
                adapter_base=adapter_base,
                pair_class=pair_class,
                compact_symbol=_compact_symbol(pair_class),
                participates_in_end_projection=position in end_projection_positions,
            )
        )
    return BasalPairingProfile(
        source_sequence_5prime=source,
        adapter_sequence_5prime=adapter,
        source_span=source_span or Span(start=Boundary(offset=0), end=Boundary(offset=len(source))),
        adapter_span=adapter_span
        or Span(start=Boundary(offset=0), end=Boundary(offset=len(adapter))),
        pairs=tuple(pairs),
        compact_profile="".join(pair.compact_symbol for pair in pairs),
    )


def derive_cohesive_end(
    *,
    side: Literal["left", "right"],
    top_sequence: str,
    binding: BasalEnzymeBinding,
    primary_strand_id: str,
    complementary_strand_id: str,
) -> CohesiveEnd:
    """Derive one exact cohesive end from the actual binding and cut coordinates."""
    if binding.reference_cut is None or binding.complement_cut is None:
        raise ValueError("cohesive-end-unavailable")
    primary = binding.reference_cut.offset
    complement = binding.complement_cut.offset
    if primary == complement:
        raise ValueError("cohesive-end-unavailable")
    span = Span(
        start=Boundary(offset=min(primary, complement)),
        end=Boundary(offset=max(primary, complement)),
    )
    aligned = top_sequence[span.start.offset : span.end.offset]
    if primary < complement:
        protruding = primary_strand_id if side == "left" else complementary_strand_id
        sequence = aligned if side == "left" else reverse_complement_iupac(aligned)
        polarity = StrandEnd.FIVE_PRIME
    else:
        protruding = complementary_strand_id if side == "left" else primary_strand_id
        sequence = reverse_complement_iupac(aligned) if side == "left" else aligned
        polarity = StrandEnd.THREE_PRIME
    return CohesiveEnd(
        product_end=side,
        protruding_strand_id=protruding,
        overhang_end=polarity,
        sequence=sequence,
        source_span=span,
        primary_cut=binding.reference_cut,
        complementary_cut=binding.complement_cut,
    )
