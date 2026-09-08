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
from hop_design.models.sequence import reverse_complement_iupac

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

    nick_boundary = payload_span.start.offset - nick_offset_nt
    if pairing_state.source_span.end.offset != nick_boundary:
        raise ValueError("Basal adapter pairing must end at the declared nick boundary.")
    retained_source = (
        reverse_complement_iupac(
            local_reference_sequence[nick_boundary : payload_span.start.offset]
        )
        if nick_offset_nt
        else ""
    )
    source_positions = tuple(
        OverheadPosition(
            coordinate_space="basal-junction",
            position=index,
            base=base,
            material_role="source",
        )
        for index, base in enumerate(retained_source)
    )
    paired_positions = tuple(
        OverheadPosition(
            coordinate_space="basal-junction",
            position=nick_offset_nt + pair.position_from_ligation,
            base=pair.adapter_base,
            material_role="adapter",
        )
        for pair in pairing_state.pairs
    )
    positions = (*source_positions, *paired_positions)
    return RetainedOverheadLedger(
        neighborhood="basal",
        reference_state_id="basal-retained-junction",
        positions=positions,
        retained_overhead_nt=len(positions),
    )


__all__ = ["basal_retained_overhead_ledger"]
