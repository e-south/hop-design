"""A search objective changes visitation, not the permitted molecular population."""

import json

import pytest

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


def objective_limits(*parameters):
    return SurveyEvaluationLimits.model_validate_json(
        json.dumps(
            {
                "local_nodes": 100,
                "local_realizations": 16,
                "release_site_pairs": 100,
                "objective": {"kind": "diversity", "parameters": list(parameters)},
            }
        )
    )


def test_only_loop_word_objectives_request_varied_sequence_starts():
    assert objective_limits("loop_word").objective.varies_foldback_members
    assert not objective_limits("loop_nt").objective.varies_foldback_members
    assert not objective_limits("left_end_word").objective.varies_foldback_members
    assert objective_limits("loop_word").objective.target_policy == "within_target/v5"
    assert (
        objective_limits("loop_word", "left_gap").objective.target_policy
        == "joint_interface_relations/v9"
    )
    assert objective_limits("left_gap").objective.target_policy == "joint_interface_relations/v9"
    assert objective_limits("foldback_arm_bp").objective.target_policy == "within_target/v3"
    assert (
        objective_limits("foldback_arm_bp", "left_gap").objective.target_policy
        == "joint_interface_relations/v9"
    )


@pytest.mark.parametrize("dimension", ["loop_nt", "loop_word"])
def test_loop_diversity_introduces_each_permitted_size_before_repeating_other_geometry(dimension):
    document = survey_document()
    document["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[7, 8], junction_offsets_nt=[0, 2], loop_lengths_nt=[3, 4, 5]
    )
    document["foldback"]["max_retained_overhead_nt"] = 24
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    before = branches.foldback_cases
    original = branches.request.model_dump(mode="json", by_alias=True)
    order = branches.search_order(objective_limits(dimension))
    first = [before[i] for i, cost in enumerate(order.costs[4]) if cost == 0]
    assert {case.loop_length_nt for case in first} == {3, 4, 5}
    assert len(first) == 3
    assert branches.foldback_cases == before
    assert branches.search_order(objective_limits(dimension)).costs == order.costs
    assert branches.request.model_dump(mode="json", by_alias=True) == original


def test_unknown_words_spread_across_arm_and_size_without_changing_legal_addresses():
    from itertools import product

    document = survey_document()
    document["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[7, 8], junction_offsets_nt=[0, 2], loop_lengths_nt=[3, 4, 5]
    )
    document["foldback"]["max_retained_overhead_nt"] = 24
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    order = branches.search_order(objective_limits("loop_word", "foldback_arm_bp"))
    first = [
        c for c, cost in zip(branches.foldback_cases, order.costs[4], strict=True) if cost == 0
    ]
    assert {(c.annealing_arm_length_bp, c.loop_length_nt) for c in first} == {
        (7, 3),
        (7, 4),
        (7, 5),
        (8, 3),
        (8, 4),
        (8, 5),
    }
    assert len(first) == 6
    assert all(c.loop_sequence is None for c in branches.foldback_cases)
    addresses = list(order.at_most(order.maximum))
    expected = set(product(*(range(size) for size in branches.geometry_sizes)))
    assert len(addresses) == len(expected)
    assert set(addresses) == expected


def test_explicit_loop_words_of_equal_length_keep_their_own_initial_priority():
    document = survey_document()
    document["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[7, 8],
        junction_offsets_nt=[0, 2],
        loop_lengths_nt=[4, 5],
        loop_sequences=["AAAA", "AAAC", "AAAAA"],
    )
    document["foldback"]["max_retained_overhead_nt"] = 24
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    order = branches.search_order(objective_limits("loop_word"))
    first = [
        c for c, cost in zip(branches.foldback_cases, order.costs[4], strict=True) if cost == 0
    ]
    assert {c.loop_sequence for c in first} == {"AAAA", "AAAC", "AAAAA"}
    assert len(first) == 3


@pytest.mark.parametrize("parameters", [[], ["loop_nt", "loop_nt"], ["loop_nt", "loop_word"]])
def test_diversity_rejects_empty_repeated_or_redundant_axes(parameters):
    with pytest.raises(ValueError, match=r"[Pp]arameter|[Ll]oop|[Dd]iversity|[Rr]epeat"):
        objective_limits(*parameters)


def test_equivalent_extension_names_do_not_count_twice():
    with pytest.raises(ValueError, match=r"[Ee]quivalent|[Rr]epeat"):
        objective_limits("foldback_arm_bp", "loop_side_paired_bp")


def test_objective_never_forms_undeclared_end_placement_combinations():
    branches = SurveyBranches(
        InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    )
    order = branches.search_order(objective_limits("left_gap", "right_gap"))
    assert len(order.costs[0]) == 2
    assert {(p.left_bp, p.right_bp) for p in branches.placements} == {(0, 0), (6, 6)}


def test_discovery_without_an_objective_keeps_existing_visitation():
    branches = SurveyBranches(
        InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    )
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=16, release_site_pairs=100)
    assert branches.search_order(limits) == branches.geometry_order
    assert "objective" not in limits.model_dump(mode="json")


def test_unknown_loop_words_do_not_become_a_fictitious_shared_sequence_class():
    from hop_design.design.construction.search.diversity import stratified_costs

    geometries = [
        {"loop_word": None, "foldback_arm_bp": 6},
        {"loop_word": None, "foldback_arm_bp": 8},
        {"loop_word": None, "foldback_arm_bp": 7},
    ]
    costs = (2, 0, 2)
    assert stratified_costs(geometries, costs, ("loop_word",)) == costs


def test_class_accounting_requires_an_achieved_value_for_every_requested_axis():
    from hop_design.design.construction.search.diversity import diversity_summary

    objective = objective_limits("loop_nt").objective
    with pytest.raises(ValueError, match="achieved"):
        diversity_summary(objective, [{"values": {}, "matches": True}])


def test_structural_allocation_does_not_collapse_exact_sequence_diversity():
    from hop_design.design.construction.search.diversity import (
        allocation_classes,
        diversity_summary,
    )

    objective = objective_limits("loop_word", "foldback_arm_bp").objective
    values = [
        {"loop_word": "AAAA", "loop_nt": 4, "foldback_arm_bp": 7},
        {"loop_word": "AACA", "loop_nt": 4, "foldback_arm_bp": 7},
        {"loop_word": "AAAAA", "loop_nt": 5, "foldback_arm_bp": 7},
    ]
    first, same_shape, new_shape = [allocation_classes(objective, row) for row in values]
    assert first[0] == same_shape[0]
    assert first[1] != same_shape[1]
    assert new_shape[0] != first[0]
    assert (
        diversity_summary(objective, [{"values": row} for row in values])["observed_classes"] == 3
    )


def test_unknown_candidate_word_keeps_known_geometry_but_is_not_complete_feedback():
    from hop_design.design.construction.search.diversity import allocation_classes

    objective = objective_limits("loop_word").objective
    candidate = {"loop_nt": 4, "loop_word": None}
    keys = allocation_classes(objective, candidate, allow_unknown=True)
    assert keys[0] is not None and keys[1] is None
    with pytest.raises(ValueError, match="achieved"):
        allocation_classes(objective, candidate)


def test_local_diversity_preserves_every_pair_and_visits_new_classes_first():
    from hop_design.design.construction.local_choices import LocalRealizationChoice
    from hop_design.design.construction.options.order import ordered_pairs
    from hop_design.models.construction.targets import FoldbackTarget

    def local(label, loop):
        return LocalRealizationChoice(
            source_result_id="local",
            realization_id=label,
            geometry=FoldbackTarget(
                junction_offset_nt=0, loop_length_nt=loop, annealing_arm_length_bp=7
            ),
            retained_overhead_nt=14 + loop,
            enzyme_ids=("nickase",),
            cohesive_end=None,
            pairing_classes=(),
            required_annealing_nt=None,
            annealing_completion_nt=None,
            material_requirements=(),
        )

    choices = {"foldback": (local("a", 4), local("b", 4), local("c", 5), local("d", 6))}
    assert [f.realization_id for f, _ in ordered_pairs(choices, None)] == ["a", "b", "c", "d"]
    ordered = list(ordered_pairs(choices, objective_limits("loop_nt").objective))
    assert [f.realization_id for f, _ in ordered] == ["a", "c", "d", "b"]
    assert all(b is None for _, b in ordered)


def test_diversity_does_not_leave_a_supported_target_after_its_first_preparation():
    from hop_design.design.construction.surveys.schedule import DiversitySchedule
    from hop_design.models.construction.surveys.targets import InterfaceTargetDomain

    schedule = DiversitySchedule(InterfaceTargetDomain(), last={}, ended=set(), supported=set())
    first = schedule.pop()
    schedule.update(first, step=0, supported=True, ended=False)
    assert schedule.pop() == first
