"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal/states.py

Discovers exact basal construction neighborhoods.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.kernel.construction.basal import BasalSequenceSolution
from hop_design.models.construction.basal import (
    BasalAdapterAnnealedComplex,
    BasalAdapterLigatedProduct,
    BasalPcrCopyState,
)
from hop_design.models.molecular_replay import (
    observe_pair,
    reindex_lineage,
)
from hop_design.models.molecular_state import (
    CovalentBond,
    LineageStrand,
    MolecularStrand,
    StrandEnd,
)
from hop_design.models.sequence import reverse_complement_iupac

from .reactions import _strand


def _pcr_states(
    solution: BasalSequenceSolution,
) -> tuple[
    BasalAdapterAnnealedComplex | None,
    BasalAdapterLigatedProduct | None,
    BasalPcrCopyState | None,
]:
    pairing_state = solution.pairing_state
    adapter_sequence = solution.adapter_sequence
    if pairing_state is None or adapter_sequence is None:
        return None, None, None
    source = _strand(
        strand_id="source-fragment",
        sequence=solution.source_precursor_sequence,
        origin_id="source-precursor",
        origin_strand=LineageStrand.PRIMARY,
    )
    adapter = _strand(
        strand_id="ligation-adapter",
        sequence=adapter_sequence,
        origin_id="ligation-adapter",
        origin_strand=LineageStrand.PRIMARY,
    )
    pairs = tuple(
        observe_pair(
            left_strand_id=source.strand_id,
            right_strand_id=adapter.strand_id,
            left_index=pairing_state.source_span.start.offset + pair.source_index,
            right_index=pair.adapter_index,
            left_base=pair.source_base,
            right_base=pair.adapter_base,
        )
        for pair in pairing_state.pairs
    )
    annealed = BasalAdapterAnnealedComplex(
        source_strand=source,
        adapter_strand=adapter,
        pairs=pairs,
    )
    bond = CovalentBond(
        upstream_strand_id=source.strand_id,
        upstream_end=StrandEnd.THREE_PRIME,
        downstream_strand_id=adapter.strand_id,
        downstream_end=StrandEnd.FIVE_PRIME,
    )
    ligated_sequence = source.sequence + adapter.sequence
    ligated_strand = MolecularStrand(
        strand_id="adapter-ligated-product",
        sequence=ligated_sequence,
        five_prime_end=source.five_prime_end,
        three_prime_end=adapter.three_prime_end,
        lineage=reindex_lineage((source.lineage, adapter.lineage)),
    )
    adapter_ligated = BasalAdapterLigatedProduct(
        source_strand=source,
        adapter_strand=adapter,
        bond=bond,
        strand=ligated_strand,
    )
    top = MolecularStrand(
        strand_id="hairpin-pcr-top",
        sequence=ligated_sequence,
        five_prime_end=ligated_strand.five_prime_end,
        three_prime_end=ligated_strand.three_prime_end,
        lineage=ligated_strand.lineage,
    )
    bottom = _strand(
        strand_id="hairpin-pcr-bottom",
        sequence=reverse_complement_iupac(ligated_sequence),
        origin_id=ligated_strand.strand_id,
        origin_strand=LineageStrand.COMPLEMENTARY,
    )
    return (
        annealed,
        adapter_ligated,
        BasalPcrCopyState(top_strand=top, bottom_strand=bottom),
    )
