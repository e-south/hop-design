"""Prepared comparisons retain the exact molecular distance and bound reuse."""

import itertools

import pytest

from hop_design.design.construction.navigation.similarity import comparison_basis, dissimilarity
from tests.unit.test_molecular_similarity import molecule


@pytest.mark.parametrize("regional", ["length_adjusted_edit", "normalized_edit"])
@pytest.mark.parametrize("ends", ["normalized_edit", "hamming"])
def test_explicit_policy_matches_prepared_and_compiled_paths(regional, ends):
    from hop_design.design.construction.navigation.numerical.comparison import PreparedComparison
    from hop_design.models.construction.variants.similarity import MolecularDistancePolicy

    rows = tuple(
        molecule(identity=str(i), loop=loop, basal=basal, gap=gap, end=end)
        for i, (loop, basal, gap, end) in enumerate(
            itertools.product(("AAAA", "AACAA", "AAA"), ("AT", "GT"), (0, 3), ("ACGT", "CGTA"))
        )
    )
    policy = MolecularDistancePolicy(
        regional_metric=regional,
        end_word_metric=ends,
        numeric_scaling="declared",
        declared_scales={"left_gap": 12, "loop_nt": 8},
    )
    basis = comparison_basis(rows, policy=policy, weights=(2, 1, 3))
    with PreparedComparison(rows, basis) as prepared:
        for i, a in enumerate(rows):
            for j, b in enumerate(rows):
                assert prepared.distance(i, j) == dissimilarity(a, b, basis).total
        if __import__("importlib.util").util.find_spec("numba") is not None:
            from hop_design.design.construction.navigation.numerical.proposals import (
                proposal_metric,
            )

            compiled, _ = proposal_metric(prepared.proposal_data())
            for i in range(len(rows)):
                for j in range(len(rows)):
                    assert compiled(i, j) == pytest.approx(prepared.distance(i, j), abs=1e-15)


def test_prepared_distances_match_the_public_explanation_and_validate_once(monkeypatch):
    from hop_design.design.construction.navigation.numerical.comparison import PreparedComparison

    rows = tuple(
        molecule(identity=str(i), loop=loop, basal=basal, gap=gap, end=end)
        for i, (loop, basal, gap, end) in enumerate(
            itertools.product(("AAAA", "AAC", "ACGTA"), ("AT", "GT"), (0, 3), ("AGTC", "AACC"))
        )
    )
    basis = comparison_basis(rows)
    expected = [[dissimilarity(a, b, basis).total for b in rows] for a in rows]
    with PreparedComparison(rows, basis, cache_entries=8) as prepared:
        # Hashing and public model allocation belong at admission, not per edge.
        def unexpected(_self):
            raise AssertionError("Revalidated a descriptor during numerical comparison")

        monkeypatch.setattr(type(rows[0]), "comparison_key", property(unexpected))
        monkeypatch.setattr(type(rows[0]), "scope_key", property(unexpected))
        assert [
            [prepared.distance(i, j) for j in range(len(rows))] for i in range(len(rows))
        ] == expected
        assert prepared.cache_info().currsize <= 8
    assert prepared.cache_info().currsize == 0
    with pytest.raises(RuntimeError, match="closed"):
        prepared.distance(0, 0)


def test_prepared_comparison_rejects_foreign_members_and_bad_indices():
    from hop_design.design.construction.navigation.numerical.comparison import PreparedComparison

    a, b = molecule(), molecule(loop="AAAC")
    basis = comparison_basis((a, b))
    with pytest.raises(ValueError, match="declared"):
        PreparedComparison((a, molecule(loop="ACGT")), basis)
    with pytest.raises(ValueError, match="scope"):
        PreparedComparison((a.model_copy(update={"stem": "TGCA"}),), basis)
    with PreparedComparison((a, b), basis) as prepared:
        for left, right in ((-1, 0), (0, 2), (True, 0)):
            with pytest.raises(ValueError, match="index"):
                prepared.distance(left, right)


def test_prepared_coincident_rows_are_zero_without_losing_members():
    from hop_design.design.construction.navigation.numerical.comparison import PreparedComparison

    rows = (molecule(), molecule(identity="another-preparation"))
    with PreparedComparison(rows, comparison_basis(rows)) as prepared:
        assert prepared.distance(0, 1) == 0
        assert len(prepared) == 2


def test_prepared_hamming_rejects_inconsistent_captured_lengths():
    from hop_design.design.construction.navigation.numerical.comparison import PreparedComparison
    from hop_design.models.construction.variants.similarity import MolecularDistancePolicy

    rows = (molecule(), molecule(end="AGT"))
    basis = comparison_basis(rows).model_copy(
        update={"distance_policy": MolecularDistancePolicy(end_word_metric="hamming")}
    )
    with pytest.raises(ValueError, match=r"equal.*length"):
        PreparedComparison(rows, basis)


def test_contact_orientation_matters_but_category_codes_are_nominal():
    from hop_design.design.construction.navigation.numerical.comparison import PreparedComparison

    a, b = molecule(basal="AT"), molecule(identity="reverse", basal="TA")
    basis = comparison_basis((a, b))
    assert dissimilarity(a, b, basis).sequence == 1
    renamed = tuple(
        row.model_copy(
            update={
                "sequences": {
                    k: tuple((x, y, "renamed-category") for x, y, _ in values)
                    if k.endswith("pairs")
                    else values
                    for k, values in row.sequences.items()
                }
            }
        )
        for row in (a, b)
    )
    with PreparedComparison(renamed, comparison_basis(renamed)) as comparison:
        assert comparison.distance(0, 1) == dissimilarity(a, b, basis).total
        if __import__("importlib.util").util.find_spec("numba") is not None:
            from hop_design.design.construction.navigation.numerical.proposals import (
                proposal_metric,
            )

            data = comparison.proposal_data()
            original, _ = proposal_metric(data)
            changed = dict(data)
            changed["words"] = 99 - data["words"]
            permuted, _ = proposal_metric(changed)
            assert original(0, 1) == permuted(0, 1)
