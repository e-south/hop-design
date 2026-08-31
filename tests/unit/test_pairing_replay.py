"""
--------------------------------------------------------------------------------
HOP Design
tests/unit/test_pairing_replay.py

Tests lineage-based lifting and composition of complete-route foldback pairings.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest

from hop_design.models.construction import SourceOrientation
from hop_design.models.construction.complete.evaluation_inputs import LinearSourceEmbedding
from hop_design.models.construction.complete.pairing_replay import (
    compose_foldback_pairings,
    lift_foldback_pairings,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import (
    EndChemistry,
    Fragment,
    LineageDirection,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
    StrandPairObservation,
)
from hop_design.models.physical import JunctionPairKind


def _lineage(
    *,
    origin_id: str,
    origin_strand: LineageStrand,
    origin_indexes: tuple[int, ...],
) -> tuple[MaterialBaseLineage, ...]:
    return tuple(
        MaterialBaseLineage(
            product_index=index,
            origin_id=origin_id,
            origin_strand=origin_strand,
            origin_index=origin_index,
        )
        for index, origin_index in enumerate(origin_indexes)
    )


def _local_foldback_pairing_fixture() -> tuple[
    tuple[Fragment, Fragment],
    StrandPairObservation,
]:
    span = Span(start=Boundary(offset=0), end=Boundary(offset=2))
    top = Fragment(
        fragment_id="top-0-2",
        precursor_strand=Strand.TOP,
        precursor_span=span,
        lineage_direction=LineageDirection.FORWARD,
        sequence="AC",
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=_lineage(
            origin_id="linear-source",
            origin_strand=LineageStrand.PRIMARY,
            origin_indexes=(0, 1),
        ),
    )
    bottom = Fragment(
        fragment_id="bottom-0-2",
        precursor_strand=Strand.BOTTOM,
        precursor_span=span,
        lineage_direction=LineageDirection.REVERSE,
        sequence="GT",
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=_lineage(
            origin_id="linear-source",
            origin_strand=LineageStrand.COMPLEMENTARY,
            origin_indexes=(1, 0),
        ),
    )
    pair = StrandPairObservation(
        left_strand_id=top.fragment_id,
        right_strand_id=bottom.fragment_id,
        left_index=0,
        right_index=1,
        left_base="A",
        right_base="T",
        kind=JunctionPairKind.WATSON_CRICK,
    )
    return (top, bottom), pair


def _selected_strand(
    strand_id: str,
    sequence: str,
    *,
    origin_id: str,
    origin_strand: LineageStrand,
) -> MolecularStrand:
    return MolecularStrand(
        strand_id=strand_id,
        sequence=sequence,
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=_lineage(
            origin_id=origin_id,
            origin_strand=origin_strand,
            origin_indexes=tuple(range(len(sequence))),
        ),
    )


def _selected_pair(source: str, complement: str) -> tuple[MolecularStrand, MolecularStrand]:
    return (
        _selected_strand(
            "selected-source",
            source,
            origin_id="source-material",
            origin_strand=LineageStrand.PRIMARY,
        ),
        _selected_strand(
            "selected-complement",
            complement,
            origin_id="complement-material",
            origin_strand=LineageStrand.COMPLEMENTARY,
        ),
    )


def test_foldback_annealing_replaces_competing_source_duplex_pairs() -> None:
    duplex = (
        StrandPairObservation(
            left_strand_id="source",
            right_strand_id="complement",
            left_index=0,
            right_index=3,
            left_base="A",
            right_base="T",
            kind=JunctionPairKind.WATSON_CRICK,
        ),
        StrandPairObservation(
            left_strand_id="source",
            right_strand_id="complement",
            left_index=1,
            right_index=2,
            left_base="C",
            right_base="G",
            kind=JunctionPairKind.WATSON_CRICK,
        ),
    )
    foldback = (
        StrandPairObservation(
            left_strand_id="source",
            right_strand_id="complement",
            left_index=0,
            right_index=2,
            left_base="A",
            right_base="G",
            kind=JunctionPairKind.HARD_MISMATCH,
        ),
    )

    assert compose_foldback_pairings(duplex, foldback) == foldback


@pytest.mark.parametrize(
    ("strands", "embedding", "expected_indexes"),
    (
        (
            _selected_pair("GGAC", "GTCC"),
            LinearSourceEmbedding(
                source_sequence="GGAC",
                complement_sequence="GTCC",
                local_reference_offset=2,
                local_complement_offset=0,
                local_source_length=2,
                source_orientation=SourceOrientation.FORWARD,
            ),
            (2, 1),
        ),
        (
            _selected_pair("ACCC", "GGGT"),
            LinearSourceEmbedding(
                source_sequence="ACCC",
                complement_sequence="GGGT",
                local_reference_offset=0,
                local_complement_offset=2,
                local_source_length=2,
                source_orientation=SourceOrientation.REVERSE_COMPLEMENT,
            ),
            (0, 3),
        ),
    ),
)
def test_foldback_pairings_lift_fragment_coordinates_through_source_periphery(
    strands: tuple[MolecularStrand, MolecularStrand],
    embedding: LinearSourceEmbedding,
    expected_indexes: tuple[int, int],
) -> None:
    fragments, local_pair = _local_foldback_pairing_fixture()

    lifted = lift_foldback_pairings(
        strands,
        fragments=fragments,
        pairings=(local_pair,),
        embedding=embedding,
        source_id="source-material",
        complement_id="complement-material",
    )

    assert lifted == (
        local_pair.model_copy(
            update={
                "left_strand_id": strands[0].strand_id,
                "right_strand_id": strands[1].strand_id,
                "left_index": expected_indexes[0],
                "right_index": expected_indexes[1],
            }
        ),
    )


def test_foldback_pairings_require_one_exact_selected_lineage_coordinate() -> None:
    fragments, local_pair = _local_foldback_pairing_fixture()
    source, complement = _selected_pair("GGAC", "GTCC")
    embedding = LinearSourceEmbedding(
        source_sequence="GGAC",
        complement_sequence="GTCC",
        local_reference_offset=2,
        local_complement_offset=0,
        local_source_length=2,
        source_orientation=SourceOrientation.FORWARD,
    )

    for strands in (
        (source,),
        (
            source,
            source.model_copy(update={"strand_id": "duplicate-selected-source"}),
            complement,
        ),
    ):
        with pytest.raises(ValueError, match="one exact selected material base"):
            lift_foldback_pairings(
                strands,
                fragments=fragments,
                pairings=(local_pair,),
                embedding=embedding,
                source_id="source-material",
                complement_id="complement-material",
            )
