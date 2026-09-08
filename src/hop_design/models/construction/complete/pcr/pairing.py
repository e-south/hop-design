"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pcr/pairing.py

Completes adapter annealing against exact invariant source-flank sequence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import (
    BasalPairingState,
    BasalPairRecord,
    BasalRealizationRecord,
)
from hop_design.models.construction.targets import BasalPairClass
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.sequence import reverse_complement_iupac

from ..basal_embedding import basal_source_offset


def complete_adapter_pairing(
    basal: BasalRealizationRecord, *, source_prefix: str
) -> BasalPairingState:
    """Extend proximal pairing with canonical pairs in the available source flank."""
    local = basal.projection.pairing_state
    if local is None:
        raise ValueError("PCR route requires the exact basal adapter-pairing authority.")
    obligation = basal.projection.annealing_obligation
    required = obligation.required_annealing_nt
    completion = obligation.annealing_completion_nt
    offset = basal_source_offset(basal, source_prefix)
    end = offset + local.source_span.end.offset
    start = end - required
    if start < 0:
        raise ValueError("Required adapter annealing exceeds the available invariant source flank.")
    source = source_prefix[start:end]
    distal = source[:completion]
    adapter = local.adapter_sequence_5prime + (reverse_complement_iupac(distal) if distal else "")
    pairs = (
        *(
            pair.model_copy(update={"source_index": pair.source_index + completion})
            for pair in local.pairs
        ),
        *(
            BasalPairRecord(
                position_from_ligation=position,
                source_index=required - 1 - position,
                adapter_index=position,
                source_base=source[required - 1 - position],
                adapter_base=adapter[position],
                pair_class=BasalPairClass.MATCH,
                compact_symbol="M",
            )
            for position in range(len(local.pairs), required)
        ),
    )
    return BasalPairingState(
        source_sequence_5prime=source,
        adapter_sequence_5prime=adapter,
        source_span=Span(start=Boundary(offset=start), end=Boundary(offset=end)),
        adapter_span=Span(start=Boundary(offset=0), end=Boundary(offset=required)),
        pairs=pairs,
        pairing_pattern=local.pairing_pattern + "M" * completion,
    )
