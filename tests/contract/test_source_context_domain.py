"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_source_context_domain.py

Checks finite source-context domains, canonical traversal, and assignment validation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from itertools import islice

import pytest

from hop_design.models.construction.complete.composition_domain import (
    composition_domain,
    source_context_count,
    validate_source_context,
)
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    DerivedSourceSsdnaPolicy,
)


def _policy(pattern: str) -> ConstrainedSourceSsdnaPolicy:
    return ConstrainedSourceSsdnaPolicy.model_validate_json(
        '{"mode":"constrain","upstream_sequence_spec":"' + pattern + '",'
        '"five_prime_end":"hydroxyl","three_prime_end":"hydroxyl"}'
    )


def test_context_order_is_local_pair_then_positional_sequence() -> None:
    policy = _policy("rym")
    assert policy.upstream_sequence_spec == "RYM"
    assert source_context_count(policy) == 8
    assert list(composition_domain(("fold",), ("base",), policy)) == [
        ("fold", "base", sequence)
        for sequence in ("ACA", "ACC", "ATA", "ATC", "GCA", "GCC", "GTA", "GTC")
    ]


def test_context_traversal_does_not_materialize_the_full_sequence_space() -> None:
    policy = _policy("N" * 100)
    assert source_context_count(policy) == 4**100
    assert list(islice(composition_domain((1, 2), (3, 4), policy), 2)) == [
        (1, 3, "A" * 100),
        (1, 3, "A" * 99 + "C"),
    ]


@pytest.mark.parametrize("sequence", (None, "AC", "NCG", "TCA", "aca"))
def test_context_assignment_rejects_missing_or_out_of_domain_bases(sequence: str | None) -> None:
    with pytest.raises(ValueError, match=r"upstream assignment|sequence domain"):
        validate_source_context(_policy("RYM"), sequence)


def test_exact_resolution_cannot_smuggle_in_a_sequence_extension() -> None:
    policy = DerivedSourceSsdnaPolicy.model_validate_json(
        '{"mode":"derive","five_prime_end":"hydroxyl","three_prime_end":"hydroxyl"}'
    )
    assert source_context_count(policy) == 1
    assert list(composition_domain((1,), (2,), policy)) == [(1, 2, None)]
    validate_source_context(policy, None)
    validate_source_context(_policy("RYM"), "ACA")
    with pytest.raises(ValueError, match="requires a constrained source"):
        validate_source_context(policy, "ACA")


@pytest.mark.parametrize("pattern", ("", "AU", "AC-"))
def test_context_policy_rejects_invalid_dna(pattern: str) -> None:
    with pytest.raises(ValueError):
        _policy(pattern)


def _length_policy(minimum: int, maximum: int, base_spec: str) -> ConstrainedSourceSsdnaPolicy:
    return ConstrainedSourceSsdnaPolicy.model_validate_json(
        json.dumps(
            {
                "mode": "constrain",
                "upstream_sequence_spec": {
                    "min_length_nt": minimum,
                    "max_length_nt": maximum,
                    "base_spec": base_spec,
                },
                "five_prime_end": "hydroxyl",
                "three_prime_end": "hydroxyl",
            }
        )
    )


def test_source_lengths_are_enumerated_before_bases_with_exact_cardinality() -> None:
    policy = _length_policy(1, 2, "m")
    assert source_context_count(policy) == 6
    assert list(composition_domain(("fold",), ("base",), policy)) == [
        ("fold", "base", sequence) for sequence in ("A", "C", "AA", "AC", "CA", "CC")
    ]
    for sequence in ("A", "C", "AA", "AC", "CA", "CC"):
        validate_source_context(policy, sequence)
    for sequence in (None, "", "AAA", "G", "AN", "ac"):
        with pytest.raises(ValueError, match=r"upstream assignment|sequence domain"):
            validate_source_context(policy, sequence)


def test_source_length_range_is_lazy_and_does_not_choose_one_length() -> None:
    policy = _length_policy(99, 100, "N")
    assert source_context_count(policy) == 4**99 + 4**100
    assert list(islice(composition_domain((1,), (2,), policy), 2)) == [
        (1, 2, "A" * 99),
        (1, 2, "A" * 98 + "C"),
    ]


@pytest.mark.parametrize(
    ("minimum", "maximum", "base_spec"),
    (
        (0, 1, "N"),
        (2, 1, "N"),
        (1, 1001, "N"),
        (1, 2, "NN"),
        (1, 2, "U"),
        (1, 2, ""),
    ),
)
def test_source_length_range_rejects_invalid_bounds_or_alphabet(
    minimum: int, maximum: int, base_spec: str
) -> None:
    with pytest.raises(ValueError):
        _length_policy(minimum, maximum, base_spec)
