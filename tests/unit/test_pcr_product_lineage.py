"""PCR lineage preserves primer handles, template ancestry and both orientations."""

import pytest

from hop_design.models.construction.complete.material import ExactConstructionMaterial, PcrPrimer
from hop_design.models.construction.complete.pcr.products import pcr_products
from hop_design.models.molecular_state import (
    EndChemistry,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
)
from hop_design.models.sequence import reverse_complement_iupac


@pytest.mark.parametrize("annealing", [2, 4])
def test_primer_and_template_lineage_have_final_indexes_from_both_strands(annealing):
    sequence = "ACGTTGCA"
    template = MolecularStrand(
        strand_id="template",
        sequence=sequence,
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=tuple(
            MaterialBaseLineage(
                product_index=i,
                origin_id="template-input",
                origin_strand=LineageStrand.PRIMARY,
                origin_index=100 + i,
            )
            for i in range(len(sequence))
        ),
    )

    def primer(word):
        return PcrPrimer(
            oligo=ExactConstructionMaterial(
                sequence_5prime=word,
                five_prime_end=EndChemistry.PHOSPHATE,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            annealing_length_nt=annealing,
        )

    forward = primer("GG" + sequence[:annealing])
    reverse = primer("TT" + reverse_complement_iupac(sequence[-annealing:]))
    top, bottom = pcr_products(
        template, forward, reverse, forward_use_id="forward", reverse_use_id="reverse"
    )
    primary, complementary = LineageStrand.PRIMARY, LineageStrand.COMPLEMENTARY
    expected = (
        [("forward", primary, i) for i in range(2 + annealing)]
        + [("template-input", primary, 100 + i) for i in range(annealing, 8 - annealing)]
        + [("reverse", complementary, i) for i in reversed(range(2 + annealing))]
    )
    assert top.sequence == "GG" + sequence + "AA"
    assert bottom.sequence == reverse_complement_iupac(top.sequence)
    assert [(v.origin_id, v.origin_strand, v.origin_index) for v in top.lineage] == expected
    assert [(v.origin_id, v.origin_strand, v.origin_index) for v in bottom.lineage] == [
        (origin, complementary if strand is primary else primary, index)
        for origin, strand, index in reversed(expected)
    ]
    assert all(
        record.product_index == i
        for strand in (top, bottom)
        for i, record in enumerate(strand.lineage)
    )
    assert all(record is not parent for record in top.lineage for parent in template.lineage)
