"""Necessary relation preserves joint end identity without handle word expansion."""

import itertools

import pytest

from hop_design.design.construction.surveys.completion.interfaces import EndPairRelations
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.support.context_completion import policy
from tests.unit.test_survey_completion_binding import product


def test_canonical_contacts_permit_all_matching_words_but_not_arbitrary_cross_pairs():
    cache = EndPairRelations(policy("N" * 24), DEFAULT_SEQUENCE_LIMITS)
    p = product()
    relation = cache.relation(p)
    assert relation is not None
    words = ["".join(b) for b in itertools.product("ACGT", repeat=4)]
    assert relation.cardinality == 256
    assert all(relation.contains(word + word) for word in words)
    assert not relation.contains("AAAAAAAC")
    q = p.model_copy(
        update={
            "ends": p.ends.model_copy(
                update={"right": p.ends.right.model_copy(update={"cohesive_end_sequence": "AAAC"})}
            )
        }
    )
    assert cache.relation(q) is relation


def test_geometry_changes_cannot_reuse_a_different_relation():
    cache = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    p = product()
    assert cache.relation(p).cardinality == 256
    assert cache.relation(product(left_gap=5)).cardinality == 0


def test_unsupported_frame_keeps_ordinary_search():
    p = product()
    p = p.model_copy(
        update={
            "release": p.release.model_copy(
                update={
                    "basal_projection": p.release.basal_projection.model_copy(
                        update={"product_end": "left"}
                    )
                }
            )
        }
    )
    assert EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS).relation(p) is None


def test_resource_exhaustion_never_returns_a_completed_empty_relation():
    limits = DEFAULT_SEQUENCE_LIMITS.model_copy(update={"max_decisions": 1})
    with pytest.raises(SequenceSetLimitError):
        EndPairRelations(policy("N" * 14), limits).relation(product())


@pytest.mark.parametrize("budget", [1, 2])
def test_pair_budget_preserves_joint_words_instead_of_independent_base_marginals(budget):
    import json

    from hop_design.models.construction.product_request import ProductRequest

    data = product().model_dump(mode="json", by_alias=True)
    data["basal"]["geometry"]["max_noncanonical_pairs"] = budget
    for i in (6, 7):
        data["basal"]["geometry"]["pairing_constraints"][i]["allowed_class"] = "any"
    p = ProductRequest.model_validate_json(json.dumps(data))
    relation = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS).relation(p)
    words = ["".join(b) for b in itertools.product("ACGT", repeat=4)]
    # The two distal end positions can differ; all other contact positions match.
    expected = {
        left + right
        for left in words
        for right in words
        if left[:2] == right[:2] and sum(a != b for a, b in zip(left, right, strict=True)) <= budget
    }
    assert {relation.member_at(i) for i in range(relation.cardinality)} == expected
