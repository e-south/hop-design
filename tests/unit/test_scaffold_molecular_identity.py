"""Physical equivalence ignores manufacturing lineage but preserves molecular properties."""

import pytest

from hop_design.models.molecular_state import EndChemistry, MolecularStrand


def strand(name="first", origin="source", sequence="ACGT"):
    return MolecularStrand.model_validate(
        {
            "strand_id": name,
            "sequence": sequence,
            "five_prime_end": EndChemistry.HYDROXYL,
            "three_prime_end": EndChemistry.HYDROXYL,
            "lineage": tuple(
                {
                    "product_index": i,
                    "origin_id": origin,
                    "origin_strand": "primary",
                    "origin_index": i,
                }
                for i in range(len(sequence))
            ),
        },
        strict=False,
    )


def test_molecular_signature_preserves_sequence_and_chemistry_not_material_origin():
    from hop_design.design.construction.discovery.molecules import molecular_signature

    def signature(item):
        return molecular_signature((item,), (), (), topology="single_stranded_hairpin")

    assert signature(strand()) == signature(strand("renamed", "different-origin"))
    assert signature(strand()) != signature(strand(sequence="AGCT"))
    phosphorylated = strand().model_copy(update={"five_prime_end": EndChemistry.PHOSPHATE})
    assert signature(strand()) != signature(phosphorylated)


def test_signature_retains_contacts_topology_and_interface_orientation():
    from hop_design.design.construction.discovery.molecules import molecular_signature
    from hop_design.models.molecular_state import CohesiveEnd, StrandPairObservation

    item = strand()
    pair = StrandPairObservation.model_validate(
        {
            "left_strand_id": "first",
            "right_strand_id": "first",
            "left_index": 0,
            "right_index": 3,
            "left_base": "A",
            "right_base": "T",
            "kind": "watson_crick",
        },
        strict=False,
    )
    interface = CohesiveEnd.model_validate(
        {
            "product_end": "left",
            "protruding_strand_id": "first",
            "overhang_end": "five_prime",
            "sequence": "A",
            "source_span": {"start": {"offset": 0}, "end": {"offset": 1}},
            "primary_cut": {"offset": 0},
            "complementary_cut": {"offset": 1},
        },
        strict=False,
    )

    def signature(pairs=(pair,), ends=(interface,), topology="single_stranded_hairpin"):
        return molecular_signature((item,), pairs, ends, topology=topology)

    assert signature() != signature(pairs=())
    assert signature() != signature(topology="linear_duplex")
    assert signature() != signature(ends=())
    changed_end = interface.model_copy(update={"product_end": "right"})
    assert signature() != signature(ends=(changed_end,))
    shifted_precursor = interface.model_copy(
        update={
            "primary_cut": interface.primary_cut.model_copy(update={"offset": 9}),
            "complementary_cut": interface.complementary_cut.model_copy(update={"offset": 10}),
        }
    )
    assert signature() == signature(ends=(shifted_precursor,))


@pytest.mark.parametrize("interstrand", [False, True])
def test_contact_endpoint_notation_does_not_change_molecular_identity(interstrand):
    from hop_design.design.construction.discovery.molecules import molecular_signature
    from hop_design.models.molecular_state import StrandPairObservation

    strands = (strand(), strand("return")) if interstrand else (strand(),)
    contact = StrandPairObservation.model_validate(
        {
            "left_strand_id": "first",
            "left_index": 0,
            "left_base": "A",
            "right_strand_id": "return" if interstrand else "first",
            "right_index": 3,
            "right_base": "T",
            "kind": "watson_crick",
        },
        strict=False,
    )
    reversed_contact = contact.model_copy(
        update={
            "left_strand_id": contact.right_strand_id,
            "left_index": contact.right_index,
            "left_base": contact.right_base,
            "right_strand_id": contact.left_strand_id,
            "right_index": contact.left_index,
            "right_base": contact.left_base,
        }
    )

    def signature(pairs):
        return molecular_signature(strands, pairs, (), topology="test")

    assert signature((contact,)) == signature((reversed_contact,))
    second = contact.model_copy(
        update={
            "left_index": 1,
            "left_base": "C",
            "right_index": 2,
            "right_base": "G",
        }
    )
    assert signature((contact, second)) == signature((second, reversed_contact))
    assert signature((contact,)) != signature((second,))
    changed_kind = contact.model_copy(update={"kind": type(contact.kind)("hard_mismatch")})
    assert signature((contact,)) != signature((changed_kind,))
    if interstrand:
        assert signature((contact,)) != molecular_signature(
            tuple(reversed(strands)), (contact,), (), topology="test"
        )
