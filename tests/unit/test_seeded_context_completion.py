"""A handle seed guides auxiliary completion without fixing the scaffold."""

import json
from itertools import product

import pytest

from hop_design.design.construction.surveys.completion.domains import ContextCompletionPlan
from hop_design.kernel.construction.sequence_order import SeededSequenceOrder
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.sequence import iupac_bases
from tests.support.context_completion import policy
from tests.unit.test_interface_survey_request import survey_document


def seeded_plan(spec="NNNN", protected=2, seed="TGCA", **kwargs):
    return ContextCompletionPlan.create(
        policy(spec),
        protected_suffix_nt=protected,
        limits=DEFAULT_SEQUENCE_LIMITS,
        handle_seed=seed,
        **kwargs,
    )


def test_seed_applies_to_every_scaffold_group_but_never_changes_its_suffix():
    plan = seeded_plan()
    assert plan.group_count == 16
    words = []
    for i in range(plan.group_count):
        group = plan.group_at(i)
        assert group.member_at(0)[0] == "TG" + group.suffix
        for j in range(group.completion_count):
            word, canonical = group.member_at(j)
            assert word.endswith(group.suffix)
            assert canonical == sum("ACGT".index(b) * 4 ** (3 - k) for k, b in enumerate(word))
            words.append(word)
    assert len(words) == len(set(words)) == 256


def test_seed_respects_correlated_permissions_and_does_not_change_lengths():
    def condition(pattern):
        b = SequenceSetBuilder(length_nt=len(pattern), max_nodes=100, max_operations=1000)
        return b.freeze(b.union(b.from_iupac("GANN"), b.from_iupac("TCTN")))

    plan = seeded_plan(condition=condition)
    assert plan.admitted_context_count == 20
    assert plan.group_at(0).member_at(0)[0] == "GAAA"
    assert plan.group_at(12).member_at(0)[0] == "TCTA"
    assert {plan.group_at(i).length_nt for i in range(plan.group_count)} == {4}


@pytest.mark.parametrize("patterns", [(), ("TGNN",), ("NCRN", "TNNN"), ("NNNN",)])
def test_seeded_seek_skips_only_proven_conflicts_in_the_same_order(patterns):
    group = seeded_plan(protected=0).group_at(0)
    # Brute-force oracle over this tiny domain only.
    expected = sorted(
        ("".join(b) for b in product("ACGT", repeat=4)),
        key=lambda word: (sum(a != b for a, b in zip(word, "TGCA", strict=True)), word),
    )
    assert [group.member_at(i)[0] for i in range(256)] == expected
    allowed = [
        i
        for i, word in enumerate(expected)
        if not any(all(b in iupac_bases(s) for b, s in zip(word, p, strict=True)) for p in patterns)
    ]
    for start in (0, 1, 5, 63, 127, 255, 256):
        assert group.next_unexcluded(start, patterns, limits=DEFAULT_SEQUENCE_LIMITS) == next(
            (i for i in allowed if i >= start), None
        )


def test_site_repair_keeps_seed_flanks_without_enumerating_other_handle_words():
    group = seeded_plan("N" * 24, 0, "T" * 24).group_at(0)
    # All words retaining this site fail. Skip the full forbidden suffix block.
    next_member = group.next_unexcluded(
        1, ("N" * 6 + "TTTTTT" + "N" * 12,), limits=DEFAULT_SEQUENCE_LIMITS
    )
    assert next_member == 19
    assert group.member_at(next_member)[0] == "T" * 6 + "A" + "T" * 17


def test_one_substitution_precedes_changes_to_two_other_bases():
    group = seeded_plan("N" * 14, 0, "GTCACATGCTGACG").group_at(0)
    first = [group.member_at(i)[0] for i in range(1 + 14 * 3)]
    assert "GTCACATGCTGTCG" in first
    assert all(sum(a != b for a, b in zip(w, "GTCACATGCTGACG", strict=True)) <= 1 for w in first)


def test_known_exact_preparation_precedes_seeded_completions():
    group = seeded_plan(preferred_contexts=("AAAC",)).group_at(1)
    assert group.member_at(0)[0] == "AAAC"
    assert group.member_at(1)[0] == "TGAC"
    assert len({group.member_at(i) for i in range(group.completion_count)}) == 16


@pytest.mark.parametrize("seed", ["", "TG", "TGCA"])
def test_distance_order_and_inverse_match_a_finite_correlated_oracle(seed):
    b = SequenceSetBuilder(length_nt=4, max_nodes=100, max_operations=1000)
    domain = b.freeze(b.union(b.from_iupac("GANN"), b.from_iupac("TCTN")))
    words = sorted(
        (
            "".join(b)
            for b in product("ACGT", repeat=4)
            if (b[0:2] == ("G", "A") or b[0:3] == ("T", "C", "T"))
        ),
        key=lambda w: (sum(a != b for a, b in zip(w, seed, strict=False)), w),
    )
    order = SeededSequenceOrder(domain, seed)
    assert [order.member_at(i) for i in range(domain.cardinality)] == words
    assert [order.rank_of(w) for w in words] == list(range(len(words)))


def test_distance_counting_has_a_declared_state_limit():
    b = SequenceSetBuilder(length_nt=4, max_nodes=100, max_operations=1000)
    domain = b.freeze(b.from_iupac("NNNA"))
    with pytest.raises(SequenceSetLimitError, match="state budget"):
        SeededSequenceOrder(domain, "TTTT", max_states=1).member_at(0)


def test_public_seed_is_explicit_normalized_and_absent_from_old_request_bytes():
    data = survey_document()
    original = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    assert "source_handle_seed" not in original.model_dump(mode="json")
    data.update(source_context_objective="paired_scaffold_completions", source_handle_seed="tgca")
    parsed = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    assert parsed.source_handle_seed == "TGCA"
    assert parsed.model_dump(mode="json")["source_handle_seed"] == "TGCA"


@pytest.mark.parametrize("change", ["all_words", "derived", "ambiguous", "empty", "oversized"])
def test_seed_rejects_unsupported_execution_or_nonexact_unbounded_input(change):
    data = survey_document()
    data.update(source_context_objective="paired_scaffold_completions", source_handle_seed="TGCA")
    if change == "all_words":
        data["source_context_objective"] = "all_words"
    elif change == "derived":
        data["materialization"]["source_preparation"]["source_ssdna"] = {
            "mode": "derive",
            "five_prime_end": "hydroxyl",
            "three_prime_end": "hydroxyl",
        }
    else:
        data["source_handle_seed"] = {"ambiguous": "NN", "empty": "", "oversized": "A" * 257}[
            change
        ]
    with pytest.raises(ValueError):
        InterfaceSurveyRequest.model_validate_json(json.dumps(data))
