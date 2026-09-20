"""
--------------------------------------------------------------------------------
HOP Design
tests/unit/test_sequence_sets.py

Checks exact compact DNA sets against independently enumerated words.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


def test_iupac_set_round_trip_recovers_exact_members_in_base_order() -> None:
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
    from hop_design.models.construction.sequence_sets import SequenceSet

    builder = SequenceSetBuilder(length_nt=3, max_nodes=100, max_operations=1000)
    exact = builder.freeze(builder.from_iupac("RNT"))
    assert exact.cardinality == 8
    restored = SequenceSet.model_validate_json(exact.model_dump_json())
    expected = ["AAT", "ACT", "AGT", "ATT", "GAT", "GCT", "GGT", "GTT"]
    assert [restored.member_at(rank) for rank in range(restored.cardinality)] == expected
    assert all(restored.contains(word) for word in expected)
    assert not restored.contains("CAT")
    assert not restored.contains("GTA")
    assert restored == exact


@settings(max_examples=30, deadline=None)
@given(
    st.sets(st.text(alphabet="ACGT", min_size=3, max_size=3), max_size=20),
    st.sets(st.text(alphabet="ACGT", min_size=3, max_size=3), max_size=20),
)
def test_set_algebra_matches_explicit_words_and_canonicalizes_insertion_order(
    left: set[str], right: set[str]
) -> None:
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    builder = SequenceSetBuilder(length_nt=3, max_nodes=10000, max_operations=100000)

    def collect(words: set[str], *, reverse: bool = False) -> int:
        root = 0
        for word in sorted(words, reverse=reverse):
            root = builder.union(root, builder.from_iupac(word))
        return root

    a, b = collect(left), collect(right)
    assert builder.freeze(a) == builder.freeze(collect(left, reverse=True))
    for root, expected in (
        (builder.union(a, b), left | right),
        (builder.intersection(a, b), left & right),
        (builder.difference(a, b), left - right),
    ):
        exact = builder.freeze(root)
        assert exact.cardinality == len(expected)
        assert [exact.member_at(i) for i in range(exact.cardinality)] == sorted(expected)
        for bases in product("ACGT", repeat=3):
            word = "".join(bases)
            assert exact.contains(word) == (word in expected)
        receiver = SequenceSetBuilder(length_nt=3, max_nodes=10000, max_operations=100000)
        assert (
            receiver.freeze(receiver.import_set(exact)).model_dump_json() == exact.model_dump_json()
        )


def test_overlapping_iupac_constraints_preserve_correlations() -> None:
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    builder = SequenceSetBuilder(length_nt=2, max_nodes=100, max_operations=1000)
    admitted = builder.union(builder.from_iupac("AN"), builder.from_iupac("NC"))
    result = builder.freeze(builder.difference(admitted, builder.from_iupac("RC")))
    assert result.cardinality == 5
    assert [result.member_at(i) for i in range(5)] == ["AA", "AG", "AT", "CC", "TC"]
    assert not result.contains("GG")


def test_large_cartesian_domain_has_exact_count_and_rank_recovery_without_members() -> None:
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    builder = SequenceSetBuilder(length_nt=128, max_nodes=1, max_operations=128)
    exact = builder.freeze(builder.from_iupac("N" * 128))
    assert exact.decisions == ()
    assert exact.cardinality == 4**128
    assert exact.member_at(0) == "A" * 128
    assert exact.member_at(4**128 - 1) == "T" * 128
    assert exact.member_at(4**127) == "C" + "A" * 127
    assert len(exact.model_dump_json()) < 400


def test_supported_maximum_variable_depth_and_empty_set() -> None:
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    builder = SequenceSetBuilder(length_nt=256, max_nodes=1000, max_operations=10000)
    member = builder.from_iupac("AC" * 128)
    complement = builder.freeze(builder.difference(1, member))
    assert complement.cardinality == 4**256 - 1
    assert not complement.contains("AC" * 128)
    assert complement.member_at(0) == "A" * 256
    assert complement.member_at(complement.cardinality - 1) == "T" * 256
    empty = builder.freeze(builder.intersection(member, builder.difference(1, member)))
    assert empty.cardinality == 0
    assert empty.decisions == ()
    assert not empty.contains("A" * 256)
    with pytest.raises(ValueError, match="rank"):
        empty.member_at(0)


@pytest.mark.parametrize(
    "name,value",
    [
        ("length_nt", 0),
        ("length_nt", 257),
        ("length_nt", True),
        ("max_nodes", 0),
        ("max_nodes", 100001),
        ("max_operations", 0),
        ("max_operations", 1000001),
    ],
)
def test_builder_rejects_unsupported_resource_declarations(name: str, value: int) -> None:
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    arguments = {"length_nt": 2, "max_nodes": 100, "max_operations": 1000}
    arguments[name] = value
    with pytest.raises(ValueError, match=name):
        SequenceSetBuilder(**arguments)


def test_builder_and_membership_reject_wrong_domains_and_handles() -> None:
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder

    builder = SequenceSetBuilder(length_nt=2, max_nodes=100, max_operations=1000)
    for pattern in ("ANZ", "", "A", "ac"):
        with pytest.raises(ValueError):
            builder.from_iupac(pattern)
    with pytest.raises(ValueError, match="alphabet"):
        builder.from_domains(("A", "Z"))
    assert builder.freeze(builder.from_domains(("A", ""))).cardinality == 0
    for handle in (-1, True, 999):
        with pytest.raises(ValueError, match="handle"):
            builder.freeze(handle)
        with pytest.raises(ValueError, match="handle"):
            builder.union(0, handle)
    exact = builder.freeze(builder.from_iupac("AN"))
    for sequence in ("NN", "A", "ac"):
        with pytest.raises(ValueError, match="exact DNA"):
            exact.contains(sequence)
    for rank in (-1, 4, True):
        with pytest.raises(ValueError, match="rank"):
            exact.member_at(rank)
    other = SequenceSetBuilder(length_nt=3, max_nodes=100, max_operations=1000)
    with pytest.raises(ValueError, match="length"):
        other.import_set(exact)


def test_algebra_exhaustion_rejects_all_subsequent_operations() -> None:
    from hop_design.kernel.construction.sequence_sets import (
        SequenceSetBuilder,
        SequenceSetLimitError,
    )

    builder = SequenceSetBuilder(length_nt=2, max_nodes=100, max_operations=2)
    root = builder.from_iupac("AC")
    with pytest.raises(SequenceSetLimitError, match="operation"):
        builder.union(root, 1)
    with pytest.raises(SequenceSetLimitError, match="operation"):
        builder.from_iupac("NN")
    with pytest.raises(SequenceSetLimitError, match="operation"):
        builder.freeze(root)


@pytest.mark.parametrize("resource", ["decision", "operation"])
def test_exhausted_builder_cannot_publish_a_partial_set(resource: str) -> None:
    from hop_design.kernel.construction.sequence_sets import (
        SequenceSetBuilder,
        SequenceSetLimitError,
    )

    builder = SequenceSetBuilder(
        length_nt=2,
        max_nodes=1 if resource == "decision" else 100,
        max_operations=1 if resource == "operation" else 100,
    )
    with pytest.raises(SequenceSetLimitError, match=resource):
        builder.from_iupac("AC")
    with pytest.raises(SequenceSetLimitError, match="exhausted"):
        builder.freeze(0)


@pytest.mark.parametrize(
    "change",
    [
        "count",
        "cycle",
        "forward",
        "position",
        "length",
        "reduced",
        "duplicate",
        "orphan",
        "root",
        "order",
        "extra",
        "coercion",
    ],
)
def test_serialized_sets_reject_corrupt_or_noncanonical_decisions(change: str) -> None:
    from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
    from hop_design.models.construction.sequence_sets import SequenceSet

    builder = SequenceSetBuilder(length_nt=2, max_nodes=100, max_operations=1000)
    value = json.loads(builder.freeze(builder.from_iupac("AC")).model_dump_json())
    if change == "count":
        value["cardinality"] = 2
    elif change == "cycle":
        value["decisions"][0]["branches"][0] = 2
    elif change == "forward":
        value["decisions"][0]["branches"][0] = 3
    elif change == "position":
        value["decisions"][1]["position_nt"] = 1
    elif change == "length":
        value["decisions"][0]["position_nt"] = 2
    elif change == "reduced":
        value["decisions"][0]["branches"] = [1] * 4
    elif change == "duplicate":
        value["decisions"].append(value["decisions"][0])
    elif change == "orphan":
        value["root"] = 2
    elif change == "root":
        value["root"] = 999
    elif change == "order":
        value["decisions"] = [
            {"position_nt": 1, "branches": [1, 0, 0, 0]},
            {"position_nt": 1, "branches": [0, 1, 0, 0]},
            {"position_nt": 0, "branches": [3, 2, 0, 0]},
        ]
        value.update(root=4, cardinality=2)
    elif change == "extra":
        value["complete"] = True
    else:
        value["length_nt"] = "2"
    with pytest.raises(ValueError):
        SequenceSet.model_validate_json(json.dumps(value))
