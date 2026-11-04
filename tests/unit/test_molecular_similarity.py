"""Similarity measures declared product differences without manufacturing identity."""

import pytest

from hop_design.design.construction.navigation.similarity import comparison_basis, dissimilarity
from hop_design.models.construction.variants.similarity import (
    MolecularDescriptor,
    MolecularDistancePolicy,
)


def molecule(*, identity="preparation-a", loop="AAAA", basal="AT", gap=0, tail=4, end="AGTC"):
    return MolecularDescriptor.model_validate(
        {
            "identity": identity,
            "stem": "ACGT",
            "endpoint": "clone_ready_duplex",
            "shape": {
                "loop_nt": len(loop),
                "loop_side_paired_bp": 2,
                "open_side_paired_positions": 1,
                "five_prime_unpaired_nt": tail,
                "three_prime_unpaired_nt": 4,
                "left_gap": gap,
                "right_gap": 0,
            },
            "sequences": {
                "loop": tuple(loop),
                "basal_pairs": ((basal[0], basal[1], "watson_crick"),),
                "foldback_pairs": (("A", "T", "watson_crick"), ("G", "C", "watson_crick")),
            },
            "interfaces": {
                "left_word": end,
                "right_word": "AACC",
                "left_polarity": "five_prime",
                "right_polarity": "five_prime",
            },
        }
    )


def test_preparation_identity_never_inflates_molecular_distance():
    a, b = molecule(), molecule(identity="different-route")
    basis = comparison_basis((a, b))
    assert dissimilarity(a, b, basis).total == 0
    assert a.comparison_key == b.comparison_key
    assert a.identity != b.identity


def test_blocks_explain_distance_and_count_length_only_in_geometry():
    a, longer, changed = molecule(), molecule(loop="AAAAA"), molecule(loop="AAAC")
    basis = comparison_basis((a, longer, changed))
    length = dissimilarity(a, longer, basis)
    substitution = dissimilarity(a, changed, basis)
    assert length.shape == 1 and length.sequence == 0
    assert substitution.shape == 0 and substitution.sequence == 0.25
    assert length.total == 0.5 and substitution.total == 0.125
    assert length.interface is None
    assert dissimilarity(changed, a, basis) == substitution


def test_zero_gap_is_a_real_value_and_interface_words_contribute():
    a, b = molecule(), molecule(gap=3, end="AGTT")
    basis = comparison_basis((a, b))
    distance = dissimilarity(a, b, basis)
    assert distance.shape == 1
    assert distance.interface == 0.25
    assert distance.total == 0.625
    assert basis.shape_scales["left_gap"] == 3


def test_context_is_frozen_and_missing_or_foreign_scope_is_not_zero():
    a, b, c = molecule(), molecule(tail=6), molecule(tail=8)
    basis = comparison_basis((a, b, c))
    assert dissimilarity(a, b, basis).shape == 0.5
    foreign = a.model_copy(update={"stem": "TGCA"})
    with pytest.raises(ValueError, match="scope"):
        comparison_basis((a, foreign))
    with pytest.raises(ValueError, match="scope"):
        dissimilarity(a, foreign, basis)
    with pytest.raises(ValueError, match="declared"):
        dissimilarity(a, molecule(tail=20), basis)


def test_shape_and_sequence_lengths_must_agree():
    a = molecule().model_dump()
    a["shape"]["loop_nt"] = 5
    with pytest.raises(ValueError, match="loop"):
        MolecularDescriptor.model_validate(a)
    a = molecule().model_dump()
    a["interfaces"] = None
    with pytest.raises(ValueError, match="interface"):
        MolecularDescriptor.model_validate(a)


def test_comparison_basis_is_order_independent_and_rejects_empty_base_tokens():
    a, b = molecule(), molecule(loop="AAAC")
    assert comparison_basis((a, b)) == comparison_basis((b, a))
    invalid = a.model_dump()
    invalid["sequences"]["loop"] = ("", "A", "A", "A")
    with pytest.raises(ValueError, match="individual bases"):
        MolecularDescriptor.model_validate(invalid)


def test_explicit_policy_changes_only_the_requested_distance_term():
    a, b = molecule(loop="AAAA", end="ACGT"), molecule(loop="AACAA", end="CGTA")
    old = comparison_basis((a, b))
    assert "distance_policy" not in old.model_dump(mode="json", by_alias=True)
    sequence = comparison_basis(
        (a, b), policy=MolecularDistancePolicy(regional_metric="normalized_edit")
    )
    ends = comparison_basis((a, b), policy=MolecularDistancePolicy(end_word_metric="hamming"))
    reference = dissimilarity(a, b, old)
    assert reference.sequence == 0 and reference.interface == 0.5
    assert dissimilarity(a, b, sequence).sequence == 0.2
    assert dissimilarity(a, b, sequence).interface == reference.interface
    assert dissimilarity(a, b, ends).interface == 1
    assert dissimilarity(a, b, ends).sequence == reference.sequence
    assert sequence.comparison_keys == old.comparison_keys == ends.comparison_keys
    assert sequence.distance_policy.regional_metric == "normalized_edit"


def test_declared_scales_are_frozen_and_never_silently_clip():
    a, b = molecule(), molecule(gap=3)
    policy = MolecularDistancePolicy(numeric_scaling="declared", declared_scales={"left_gap": 12})
    basis = comparison_basis((a, b), policy=policy)
    assert dissimilarity(a, b, basis).shape == 0.25
    with pytest.raises(ValueError, match="scale"):
        comparison_basis(
            (a, b),
            policy=MolecularDistancePolicy(
                numeric_scaling="declared", declared_scales={"left_gap": 2}
            ),
        )
    with pytest.raises(ValueError, match="scale"):
        comparison_basis(
            (a, b),
            policy=MolecularDistancePolicy(
                numeric_scaling="declared", declared_scales={"loop_nt": 12}
            ),
        )


def test_positional_ends_require_equal_lengths_and_keep_orientation():
    a, b = molecule(end="AGTC"), molecule(end="GACT")
    policy = MolecularDistancePolicy(end_word_metric="hamming")
    assert dissimilarity(a, b, comparison_basis((a, b), policy=policy)).interface == 1
    with pytest.raises(ValueError, match=r"equal.*length"):
        comparison_basis((a, molecule(end="AGT")), policy=policy)


def test_policy_rejects_unused_scales_and_keeps_constant_features_out():
    with pytest.raises(ValueError, match="declared"):
        MolecularDistancePolicy(declared_scales={"loop_nt": 10})
    a, b = molecule(), molecule(identity="another-route")
    basis = comparison_basis(
        (a, b), policy=MolecularDistancePolicy(regional_metric="normalized_edit")
    )
    assert dissimilarity(a, b, basis).total == 0
    assert not basis.shape_scales and not basis.sequence_keys and not basis.interface_keys
