"""Pure basal-junction pairing and strand mechanics."""

from __future__ import annotations

from typing import Literal

from hop_design.models.basal import (
    BasalPairingRequest,
    BasalPairKind,
    BasalPairObservation,
    BasalPairProfile,
)
from hop_design.models.junction import Strand
from hop_design.models.sequence import reverse_complement_iupac

BasalSite = Literal["S3", "S2", "S1", "S0"]
_SITES: tuple[BasalSite, ...] = ("S3", "S2", "S1", "S0")


def classify_basal_pairing(request: BasalPairingRequest) -> BasalPairProfile:
    """Classify antiparallel arm pairs without applying selection policy."""
    pairs: list[BasalPairObservation] = []
    for position, site in enumerate(_SITES):
        right_index = 3 - position
        left_base = request.left_arm[position]
        right_base = request.right_arm[right_index]
        aligned_right_base = reverse_complement_iupac(right_base)
        compact_symbol: Literal["M", "W", "X"]
        if left_base == aligned_right_base:
            kind = BasalPairKind.WATSON_CRICK
            compact_symbol = "M"
        elif request.allow_gt_wobble and (left_base, right_base) in {
            ("G", "T"),
            ("T", "G"),
        }:
            kind = BasalPairKind.GT_WOBBLE
            compact_symbol = "W"
        else:
            kind = BasalPairKind.HARD_MISMATCH
            compact_symbol = "X"
        pairs.append(
            BasalPairObservation(
                position=position,
                site=site,
                left_index=position,
                right_index=right_index,
                left_base=left_base,
                right_base=right_base,
                kind=kind,
                compact_symbol=compact_symbol,
            )
        )

    compact_profile = "".join(pair.compact_symbol for pair in pairs)
    watson_crick_count = compact_profile.count("M")
    wobble_count = compact_profile.count("W")
    hard_mismatch_count = compact_profile.count("X")
    pair_tuple = (pairs[0], pairs[1], pairs[2], pairs[3])
    return BasalPairProfile(
        left_arm=request.left_arm,
        right_arm=request.right_arm,
        compact_profile_s3_s2_s1_s0=compact_profile,
        compact_profile_payload_outward=compact_profile[::-1],
        pairs=pair_tuple,
        watson_crick_count=watson_crick_count,
        wobble_count=wobble_count,
        hard_mismatch_count=hard_mismatch_count,
        non_watson_crick_count=wobble_count + hard_mismatch_count,
        middle_hard_mismatch_count=sum(
            pair.kind is BasalPairKind.HARD_MISMATCH for pair in pair_tuple[1:3]
        ),
        support_score=float(watson_crick_count) + 0.5 * float(wobble_count),
        disruption_score=float(hard_mismatch_count) + 0.5 * float(wobble_count),
        terminal_pair_kind=pair_tuple[-1].kind,
    )


def surviving_strand(nicked_strand: Strand) -> Strand:
    """Return the strand physically opposite one declared nicked strand."""
    if nicked_strand is Strand.TOP:
        return Strand.BOTTOM
    return Strand.TOP


__all__ = ["classify_basal_pairing", "surviving_strand"]
