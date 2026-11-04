"""The interface universe survives execution budgets and traversal order."""

from collections import Counter

import pytest

from hop_design.models.construction.surveys.targets import InterfaceTargetDomain


def test_complete_four_base_domain_contains_every_ordered_pair():
    domain = InterfaceTargetDomain()
    assert domain.left_count == domain.right_count == 256
    assert domain.pair_count == 65_536
    assert domain.pair_at(0) == ("AAAA", "AAAA")
    assert domain.pair_at(1) == ("AAAA", "AAAC")
    assert domain.pair_at(256) == ("AAAC", "AAAA")
    assert domain.pair_at(65_535) == ("TTTT", "TTTT")
    pairs = [domain.pair_at(i) for i in range(domain.pair_count)]
    assert len(set(pairs)) == 65_536
    assert set(Counter(left for left, _ in pairs).values()) == {256}
    assert set(Counter(right for _, right in pairs).values()) == {256}


def test_coverage_traversal_visits_both_marginals_before_repeating_and_is_reversible():
    domain = InterfaceTargetDomain()
    first = [domain.pair_at(domain.coverage_ordinal(i)) for i in range(256)]
    assert len({left for left, _ in first}) == 256
    assert len({right for _, right in first}) == 256
    ordinals = [domain.coverage_ordinal(i) for i in range(domain.pair_count)]
    assert len(set(ordinals)) == 65_536
    assert min(ordinals) == 0 and max(ordinals) == 65_535
    assert [domain.coverage_rank(i) for i in ordinals] == list(range(65_536))


def test_explicit_subdomains_remain_exact_and_canonical():
    domain = InterfaceTargetDomain.model_validate_json(
        '{"left_words":["TTTT","AAAA"],"right_words":["CCCC","GGGG","TTTT"]}'
    )
    assert domain.pair_count == 6
    assert [domain.pair_at(domain.coverage_ordinal(i)) for i in range(6)] == [
        ("AAAA", "CCCC"),
        ("TTTT", "GGGG"),
        ("AAAA", "GGGG"),
        ("TTTT", "TTTT"),
        ("AAAA", "TTTT"),
        ("TTTT", "CCCC"),
    ]
    assert [domain.coverage_rank(domain.coverage_ordinal(i)) for i in range(6)] == list(range(6))


@pytest.mark.parametrize("words", [[], ["AAAA", "AAAA"], ["NNNN"], ["AAA"], ["AAAAA"]])
def test_invalid_exact_word_domains_fail_closed(words):
    import json

    with pytest.raises(ValueError):
        InterfaceTargetDomain.model_validate_json(json.dumps({"left_words": words}))


@pytest.mark.parametrize("index", [-1, 65_536, True, 0.5])
def test_target_addresses_reject_outside_and_noninteger_indexes(index):
    domain = InterfaceTargetDomain()
    for operation in (domain.pair_at, domain.coverage_ordinal, domain.coverage_rank):
        with pytest.raises(ValueError):
            operation(index)
