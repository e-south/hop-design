"""Exact terminal ancestry separates discarded handles from retained sequence."""

import pytest

from hop_design.design.construction.navigation.numerical.comparison import PreparedComparison
from hop_design.design.construction.navigation.similarity import comparison_basis, dissimilarity
from hop_design.export.construction.survey.comparison_features import comparison_features
from hop_design.models.construction.variants.similarity import MolecularDescriptor
from tests.unit.test_molecular_similarity import molecule


def with_retention(row, five="", three=""):
    data = row.model_dump()
    data["retained_terminal_bases"] = {"five_prime": tuple(five), "three_prime": tuple(three)}
    return MolecularDescriptor.model_validate(data)


def test_discarded_handles_do_not_separate_insert_scaffolds_or_drop_preparations():
    a = with_retention(molecule(identity="first", tail=4))
    b = with_retention(molecule(identity="other", tail=8))
    assert a.shape["five_prime_unpaired_nt"] == 4
    assert b.shape["five_prime_unpaired_nt"] == 8
    assert a.comparison_key == b.comparison_key
    assert a.identity != b.identity
    basis = comparison_basis((a, b))
    assert basis.schema_id == "hop.molecular-comparison/v2"
    assert "five_prime_unpaired_nt" not in basis.shape_scales
    assert dissimilarity(a, b, basis).total == 0
    with PreparedComparison((a, b), basis) as fast:
        assert fast.distance(0, 1) == 0
    packet = comparison_features((a, b), basis, (a.identity, b.identity))
    assert packet["basis"]["schema_id"] == "hop.molecular-comparison/v2"
    fields = packet["columns"]
    assert "shape.five_prime_retained_tail_nt" in {f["key"] for f in fields}
    assert "shape.five_prime_unpaired_nt" not in {f["key"] for f in fields}
    from hop_design.design.construction.navigation.similarity_layout import (
        build_molecular_landscape,
    )

    landscape = build_molecular_landscape((a, b), snapshot_digest="sha256:" + "1" * 64)
    assert landscape.algorithm == "coincident"
    assert len(landscape.coordinates) == 1
    assert {p.identity for p in landscape.preparations} == {a.identity, b.identity}


def test_retained_tail_sequence_and_extent_still_contribute():
    a = with_retention(molecule(identity="first"), "AC")
    b = with_retention(molecule(identity="second", tail=6), "AG")
    c = with_retention(molecule(identity="third", tail=8), "ACG")
    basis = comparison_basis((a, b, c))
    assert basis.shape_scales["five_prime_retained_tail_nt"] == 1
    assert dissimilarity(a, b, basis).shape == 0
    assert dissimilarity(a, b, basis).sequence == 0.5
    assert dissimilarity(a, c, basis).shape == 1
    with PreparedComparison((a, b, c), basis) as fast:
        for i, x in enumerate((a, b, c)):
            for j, y in enumerate((a, b, c)):
                assert fast.distance(i, j) == dissimilarity(x, y, basis).total


def test_hairpin_endpoint_keeps_its_full_terminal_geometry():
    rows = []
    for tail in (4, 8):
        d = molecule(tail=tail).model_dump()
        d.update(endpoint="adapter_ligated_hairpin", interfaces=None)
        d["shape"] = {k: v for k, v in d["shape"].items() if not k.endswith("gap")}
        rows.append(MolecularDescriptor.model_validate(d))
    assert dissimilarity(*rows, comparison_basis(tuple(rows))).shape == 1
    with pytest.raises(ValueError, match="released"):
        with_retention(rows[0])


def test_legacy_scope_cannot_be_silently_reinterpreted_and_retention_is_bounded():
    old = molecule()
    assert "retained_terminal_bases" not in old.model_dump()
    current = with_retention(old)
    with pytest.raises(ValueError, match="scope"):
        comparison_basis((old, current))
    with pytest.raises(ValueError, match="terminal"):
        with_retention(old, "AAAAA")


@pytest.mark.parametrize(
    ("schema", "shape", "sequences"),
    [
        ("hop.molecular-comparison/v1", {"five_prime_retained_tail_nt": 1}, ()),
        ("hop.molecular-comparison/v1", {}, ("five_prime_retained_tail",)),
        ("hop.molecular-comparison/v2", {"five_prime_unpaired_nt": 1}, ()),
    ],
)
def test_comparison_version_rejects_other_terminal_semantics(schema, shape, sequences):
    from hop_design.models.construction.variants.similarity import MolecularComparisonBasis

    data = comparison_basis((molecule(),)).model_dump(by_alias=True)
    data.update(schema=schema, shape_scales=shape, sequence_keys=sequences)
    with pytest.raises(ValueError, match="terminal"):
        MolecularComparisonBasis.model_validate(data)


def test_primer_supplied_copies_preserve_template_dependence_but_handles_do_not():
    from types import SimpleNamespace as NS

    from hop_design.design.construction.navigation.molecular_descriptor import _retained_terminals
    from hop_design.models.construction.complete.pcr.authority import PrimerExtensionAuthority
    from hop_design.models.molecular_state import LineageStrand, MaterialBaseLineage

    def base(origin, index, product=0):
        return MaterialBaseLineage(
            origin_id=origin,
            origin_index=index,
            origin_strand=LineageStrand.PRIMARY,
            product_index=product,
        )

    template = NS(sequence="ACGTACGTACGT", lineage=tuple(base("source", i, i) for i in range(12)))
    pre = NS(state_id="template", molecules=(template,))
    anatomy = NS(
        state=pre,
        paired_primary_span=NS(start=NS(offset=3)),
        paired_return_span=NS(end=NS(offset=9)),
    )
    # Pure projection seam: compiler admission is exercised by integration tests.
    pcr = PrimerExtensionAuthority.model_construct(
        pre_state_id="template",
        forward_primer=NS(annealing_length_nt=3, oligo=NS(sequence_5prime="GGACG")),
        reverse_primer=NS(annealing_length_nt=3, oligo=NS(sequence_5prime="CCACG")),
        forward_primer_use=NS(use_id="forward"),
        reverse_primer_use=NS(use_id="reverse"),
    )
    final = NS(
        phase=NS(value="clone_ready_duplex"),
        molecules=(
            NS(
                lineage=(
                    base("forward", 2),
                    base("forward", 4),
                    base("reverse", 2),
                    base("forward", 0),
                )
            ),
        ),
    )
    route = NS(
        final_product=NS(reference=NS(endpoint=NS(value="clone_ready_duplex"))),
        construction_program=NS(states=(final,), transitions=(NS(pcr_authority=pcr),)),
        source_preparation=NS(produced_material_bindings=(), product_state=NS(molecules=())),
    )
    assert _retained_terminals(route, anatomy) == {"five_prime": ("A", "G"), "three_prime": ("T",)}
