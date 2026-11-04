"""Pin terminal coordinate selection independently of repeated sequence words."""

import pytest

from hop_design.export.construction.handoff.end_inspection import end_lineage
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.molecular_state import (
    CohesiveEnd,
    EndChemistry,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
    StrandEnd,
)


@pytest.mark.parametrize(
    "polarity,indexes", [(StrandEnd.FIVE_PRIME, [0, 1, 2]), (StrandEnd.THREE_PRIME, [6, 7, 8])]
)
def test_end_lineage_uses_polarity_not_first_substring(polarity, indexes) -> None:
    strand = MolecularStrand(
        strand_id="synthetic-strand",
        sequence="GACTTTGAC",
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=tuple(
            MaterialBaseLineage(
                product_index=i,
                origin_id="synthetic-material-use",
                origin_strand=LineageStrand.COMPLEMENTARY,
                origin_index=20 - i,
            )
            for i in range(9)
        ),
    )
    end = CohesiveEnd(
        product_end="right",
        protruding_strand_id=strand.strand_id,
        overhang_end=polarity,
        sequence="GAC",
        source_span=Span(start=Boundary(offset=10), end=Boundary(offset=13)),
        primary_cut=Boundary(offset=10 if polarity is StrandEnd.FIVE_PRIME else 13),
        complementary_cut=Boundary(offset=13 if polarity is StrandEnd.FIVE_PRIME else 10),
    )
    origins = end_lineage(end, strand)
    assert [item.product_index for item in origins] == indexes
    assert [item.origin_index for item in origins] == [20 - i for i in indexes]
