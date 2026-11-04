"""Known source handles guide completion without replacing protected scaffold choices."""

import json
from itertools import product

import pytest

from hop_design.design.construction.surveys.completion.domains import ContextCompletionPlan
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.support.context_completion import policy
from tests.unit.test_interface_survey_request import survey_document


def preferred_plan(spec="NNNN", protected=2, preferred=("TTAC",)):
    return ContextCompletionPlan.create(
        policy(spec),
        protected_suffix_nt=protected,
        limits=DEFAULT_SEQUENCE_LIMITS,
        preferred_contexts=preferred,
    )


def test_preferred_handle_changes_completion_order_not_scaffold_groups_or_addresses():
    plan = preferred_plan()
    group = plan.group_at(1)
    assert group.suffix == "AC"
    assert group.member_at(0) == ("TTAC", 241)
    assert group.member_at(1) == ("AAAC", 1)
    assert plan.group_count == 16 and plan.raw_context_count == 256
    words = [
        plan.group_at(g).member_at(i)[0]
        for g in range(plan.group_count)
        for i in range(plan.group_at(g).completion_count)
    ]
    assert len(words) == len(set(words)) == 256
    assert set(words) == {"".join(bases) for bases in product("ACGT", repeat=4)}


def test_recognition_preference_and_exclusion_seek_survive_failed_preferred_handle():
    builder = SequenceSetBuilder(length_nt=4, max_nodes=100, max_operations=1000)
    group = preferred_plan().group_at(1, preferred=builder.freeze(builder.from_iupac("GANN")))
    assert group.member_at(0) == ("TTAC", 241)
    assert group.member_at(1) == ("GAAC", 129)
    assert group.member_at(2) == ("AAAC", 1)
    assert group.next_unexcluded(0, ("TNNN",), limits=DEFAULT_SEQUENCE_LIMITS) == 1
    assert group.next_unexcluded(1, ("GNNN", "TNNN"), limits=DEFAULT_SEQUENCE_LIMITS) == 2
    assert group.next_unexcluded(0, ("NNNN",), limits=DEFAULT_SEQUENCE_LIMITS) is None
    assert len({group.member_at(i) for i in range(group.completion_count)}) == 16


def test_preference_outside_permission_never_introduces_a_word_or_length():
    plan = preferred_plan("ANNN", preferred=("TTAC", "AAC", "AAAAA"))
    assert plan.group_count == 16 and plan.raw_context_count == 64
    assert plan.group_at(1).member_at(0) == ("AAAC", 1)


def test_preferred_context_request_is_explicit_bounded_and_legacy_bytes_stay_small():
    data = survey_document()
    original = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    assert "preferred_source_contexts" not in original.model_dump(mode="json")
    data.update(source_context_objective="paired_scaffold_completions")
    data["preferred_source_contexts"] = ["ttac", "gaac"]
    parsed = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    assert parsed.preferred_source_contexts == ("GAAC", "TTAC")
    data["preferred_source_contexts"] = ["TTAC", "ttac"]
    with pytest.raises(ValueError, match="distinct"):
        InterfaceSurveyRequest.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("change", ["all_words", "fixed_source", "ambiguous", "oversized"])
def test_preference_cannot_be_silently_ignored_or_expand_an_unbounded_roster(change):
    data = survey_document()
    data.update(
        source_context_objective="paired_scaffold_completions", preferred_source_contexts=["TTAC"]
    )
    if change == "all_words":
        data["source_context_objective"] = "all_words"
    elif change == "fixed_source":
        data["materialization"]["source_preparation"]["source_ssdna"] = {
            "mode": "derive",
            "five_prime_end": "hydroxyl",
            "three_prime_end": "hydroxyl",
        }
    else:
        data["preferred_source_contexts"] = ["NNNN"] if change == "ambiguous" else ["A"] * 17
    with pytest.raises(ValueError):
        InterfaceSurveyRequest.model_validate_json(json.dumps(data))
