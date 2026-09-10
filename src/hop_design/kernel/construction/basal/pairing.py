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
    BasalPairingState,
    BasalPairRecord,
    derive_basal_pair_class,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.sequence import normalize_dna_sequence


def _compact_symbol(pair_class: BasalPairClass) -> Literal["M", "W", "X"]:
    if pair_class is BasalPairClass.MATCH:
        return "M"
    if pair_class is BasalPairClass.WOBBLE:
        return "W"
    return "X"


def resolve_basal_pairing_state(
    *,
    source_sequence_5prime: str,
    adapter_sequence_5prime: str,
    source_span: Span | None = None,
    adapter_span: Span | None = None,
    end_projection_positions: tuple[int, ...] = (),
) -> BasalPairingState:
    """Classify exact antiparallel pairs outward from the adapter's ligating end."""
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
                position_from_ligation=position,
                source_index=source_index,
                adapter_index=position,
                source_base=source_base,
                adapter_base=adapter_base,
                pair_class=pair_class,
                compact_symbol=_compact_symbol(pair_class),
                participates_in_end_projection=position in end_projection_positions,
            )
        )
    return BasalPairingState(
        source_sequence_5prime=source,
        adapter_sequence_5prime=adapter,
        source_span=source_span or Span(start=Boundary(offset=0), end=Boundary(offset=len(source))),
        adapter_span=adapter_span
        or Span(start=Boundary(offset=0), end=Boundary(offset=len(adapter))),
        pairs=tuple(pairs),
        pairing_pattern="".join(pair.compact_symbol for pair in pairs),
    )
