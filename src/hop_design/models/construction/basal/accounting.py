"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal/accounting.py

Replays retained-overhead accounting for one basal junction view.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.coordinates import Span

from ..accounting import OverheadPosition, RetainedOverheadLedger
from .pairing import BasalPairingState


def basal_retained_overhead_ledger(
    *,
    local_reference_sequence: str,
    payload_span: Span,
    pairing_state: BasalPairingState,
    nick_offset_nt: int,
) -> RetainedOverheadLedger:
    """Return one position-level ledger for the retained basal junction."""

    paired_positions = tuple(
        OverheadPosition(
            coordinate_space="basal-junction",
            position=pair.position_from_ligation,
            base=pair.adapter_base,
            material_role="adapter",
        )
        for pair in pairing_state.pairs
    )
    pair_count = len(paired_positions)
    additional_count = max(0, nick_offset_nt - pair_count)
    source_start = payload_span.start.offset - pair_count
    if source_start < additional_count:
        raise ValueError("Retained overhead extends outside the basal local reference sequence.")
    additional_positions = tuple(
        OverheadPosition(
            coordinate_space="basal-junction",
            position=pair_count + index,
            base=local_reference_sequence[source_start - index - 1],
            material_role="source",
        )
        for index in range(additional_count)
    )
    positions = (*paired_positions, *additional_positions)
    return RetainedOverheadLedger(
        neighborhood="basal",
        reference_state_id="basal-retained-junction",
        positions=positions,
        retained_overhead_nt=len(positions),
    )


__all__ = ["basal_retained_overhead_ledger"]
