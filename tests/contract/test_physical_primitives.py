"""Exhaustive contracts for shared physical pair and orientation primitives."""

from __future__ import annotations

import itertools

import pytest

from hop_design.kernel.molecular_states import observe_pair
from hop_design.models.junction import JunctionPairObservation
from hop_design.models.physical import (
    JunctionPairKind,
    SiteOrientation,
    Strand,
    classify_literal_pair,
    opposite_strand,
    orient_nick_geometry,
    orient_release_geometry,
)

_BASES = ("A", "C", "G", "T")
_WATSON_CRICK = {("A", "T"), ("C", "G"), ("G", "C"), ("T", "A")}
_GT_WOBBLES = {("G", "T"), ("T", "G")}


@pytest.mark.parametrize(("left_base", "right_base"), tuple(itertools.product(_BASES, repeat=2)))
def test_literal_pair_classification_is_exhaustive(
    left_base: str,
    right_base: str,
) -> None:
    pair = (left_base, right_base)
    expected = (
        JunctionPairKind.WATSON_CRICK
        if pair in _WATSON_CRICK
        else JunctionPairKind.GT_WOBBLE
        if pair in _GT_WOBBLES
        else JunctionPairKind.HARD_MISMATCH
    )

    physical_kind = classify_literal_pair(left_base=left_base, right_base=right_base)
    junction_pair = JunctionPairObservation(
        left_index=0,
        right_index=0,
        left_base=left_base,
        right_base=right_base,
        kind=expected,
    )
    molecular_pair = observe_pair(
        left_strand_id="left",
        right_strand_id="right",
        left_index=0,
        right_index=0,
        left_base=left_base,
        right_base=right_base,
    )

    assert physical_kind is expected
    assert junction_pair.kind is physical_kind
    assert molecular_pair.kind is physical_kind


@pytest.mark.parametrize(
    ("strand", "expected"),
    ((Strand.TOP, Strand.BOTTOM), (Strand.BOTTOM, Strand.TOP)),
)
def test_opposite_strand_is_exact_and_involutive(strand: Strand, expected: Strand) -> None:
    assert opposite_strand(strand) is expected
    assert opposite_strand(opposite_strand(strand)) is strand


@pytest.mark.parametrize(
    ("target_strand", "expected_orientation", "expected_motif", "expected_cut"),
    (
        (Strand.TOP, SiteOrientation.FORWARD, "ACGTA", 2),
        (Strand.BOTTOM, SiteOrientation.REVERSE, "TACGT", 3),
    ),
)
def test_nick_geometry_has_one_orientation_authority(
    target_strand: Strand,
    expected_orientation: SiteOrientation,
    expected_motif: str,
    expected_cut: int,
) -> None:
    geometry = orient_nick_geometry(
        motif_top_5to3="ACGTA",
        native_nicked_strand=Strand.TOP,
        cut_offset=2,
        target_strand=target_strand,
    )

    assert geometry.orientation is expected_orientation
    assert geometry.motif_top_5to3 == expected_motif
    assert geometry.cut_offset == expected_cut


@pytest.mark.parametrize(
    ("orientation", "expected_motif", "expected_top_cut", "expected_bottom_cut"),
    (
        (SiteOrientation.FORWARD, "ACGTA", 1, 3),
        (SiteOrientation.REVERSE, "TACGT", 2, 4),
    ),
)
def test_release_geometry_has_one_orientation_authority(
    orientation: SiteOrientation,
    expected_motif: str,
    expected_top_cut: int,
    expected_bottom_cut: int,
) -> None:
    geometry = orient_release_geometry(
        motif_top_5to3="ACGTA",
        top_cut_offset=1,
        bottom_cut_offset=3,
        orientation=orientation,
    )

    assert geometry.orientation is orientation
    assert geometry.motif_top_5to3 == expected_motif
    assert geometry.top_cut_offset == expected_top_cut
    assert geometry.bottom_cut_offset == expected_bottom_cut
