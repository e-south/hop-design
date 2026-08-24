"""Pure authorities for literal pair, strand, and cut-site orientation semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hop_design.models.sequence import reverse_complement_iupac


class Strand(StrEnum):
    """A declared strand role in a duplex representation."""

    TOP = "top"
    BOTTOM = "bottom"


class SiteOrientation(StrEnum):
    """The orientation of a recognition motif against the stored top strand."""

    FORWARD = "forward"
    REVERSE = "reverse"


class JunctionPairKind(StrEnum):
    """Physical classification of one aligned nucleotide pair."""

    WATSON_CRICK = "watson_crick"
    GT_WOBBLE = "gt_wobble"
    HARD_MISMATCH = "hard_mismatch"


@dataclass(frozen=True, slots=True)
class OrientedNickGeometry:
    """One nicking motif and cut offset in stored-top-strand coordinates."""

    orientation: SiteOrientation
    motif_top_5to3: str
    cut_offset: int


@dataclass(frozen=True, slots=True)
class OrientedReleaseGeometry:
    """One release motif and duplex cuts in stored-top-strand coordinates."""

    orientation: SiteOrientation
    motif_top_5to3: str
    top_cut_offset: int
    bottom_cut_offset: int


def classify_literal_pair(*, left_base: str, right_base: str) -> JunctionPairKind:
    """Return the sole physical pair kind implied by two exact DNA bases."""
    aligned_right = reverse_complement_iupac(right_base)
    if left_base == aligned_right:
        return JunctionPairKind.WATSON_CRICK
    if (left_base, right_base) in {("G", "T"), ("T", "G")}:
        return JunctionPairKind.GT_WOBBLE
    return JunctionPairKind.HARD_MISMATCH


def opposite_strand(strand: Strand) -> Strand:
    """Return the strand physically opposite one declared strand."""
    return Strand.BOTTOM if strand is Strand.TOP else Strand.TOP


def orient_nick_geometry(
    *,
    motif_top_5to3: str,
    native_nicked_strand: Strand,
    cut_offset: int,
    target_strand: Strand,
) -> OrientedNickGeometry:
    """Orient a nicking motif so it cuts the requested physical strand."""
    if native_nicked_strand is target_strand:
        return OrientedNickGeometry(
            orientation=SiteOrientation.FORWARD,
            motif_top_5to3=motif_top_5to3,
            cut_offset=cut_offset,
        )
    return OrientedNickGeometry(
        orientation=SiteOrientation.REVERSE,
        motif_top_5to3=reverse_complement_iupac(motif_top_5to3),
        cut_offset=len(motif_top_5to3) - cut_offset,
    )


def orient_release_geometry(
    *,
    motif_top_5to3: str,
    top_cut_offset: int,
    bottom_cut_offset: int,
    orientation: SiteOrientation,
) -> OrientedReleaseGeometry:
    """Orient a duplex-release motif and both cut offsets together."""
    if orientation is SiteOrientation.FORWARD:
        return OrientedReleaseGeometry(
            orientation=orientation,
            motif_top_5to3=motif_top_5to3,
            top_cut_offset=top_cut_offset,
            bottom_cut_offset=bottom_cut_offset,
        )
    motif_nt = len(motif_top_5to3)
    return OrientedReleaseGeometry(
        orientation=orientation,
        motif_top_5to3=reverse_complement_iupac(motif_top_5to3),
        top_cut_offset=motif_nt - bottom_cut_offset,
        bottom_cut_offset=motif_nt - top_cut_offset,
    )


__all__ = [
    "JunctionPairKind",
    "OrientedNickGeometry",
    "OrientedReleaseGeometry",
    "SiteOrientation",
    "Strand",
    "classify_literal_pair",
    "opposite_strand",
    "orient_nick_geometry",
    "orient_release_geometry",
]
