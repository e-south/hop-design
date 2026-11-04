"""Known local emptiness changes priority, never permissions or unknown status."""

from itertools import product
from types import SimpleNamespace

import pytest

from hop_design.design.construction.surveys.coordinates import coordinate_at
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.design.construction.surveys.navigation.admission_order import (
    MAX_FOLDBACK_PROBES,
    admitted_geometry_order,
)
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.product_pairing import ProductConstraintConflict
from hop_design.models.construction.targets import FoldbackTarget
from hop_design.models.physical import Strand
from tests.unit.test_design_diversity import objective_limits


def case_order(costs=(0, 1, 2), *, context="paired_scaffold_completions"):
    sizes = (1, 1, 1, 1, len(costs), 1)
    order = GeometryOrder(((0,), (0,), (0,), (0,), costs, (0,)))
    branches = SimpleNamespace(
        request=SimpleNamespace(source_context_objective=context),
        geometry_sizes=sizes,
        search_order=lambda limits: order,
        product=lambda target, branch, limits: coordinate_at(sizes, branch)[4],
        foldback_cases=tuple(
            FoldbackTarget(
                annealing_arm_length_bp=6,
                junction_offset_nt=0,
                loop_length_nt=4,
                nick_strand=Strand.TOP,
            )
            for _ in costs
        ),
    )
    return branches, order


def test_first_admitted_member_of_each_requested_shape_has_equal_priority():
    branches, before = case_order((0, 1, 0, 1, 2, 3))
    branches.foldback_cases = tuple(
        branches.foldback_cases[i].model_copy(
            update={"annealing_arm_length_bp": arm, "junction_offset_nt": join}
        )
        for i, (arm, join) in enumerate(((6, 0), (6, 1), (8, 0), (8, 1), (8, 2), (8, 3)))
    )
    partitions = SimpleNamespace(
        foldback_population=lambda i: SimpleNamespace(parts=(0, 3, 0, 0, 3, 3)[i])
    )
    after = admitted_geometry_order(
        branches, objective_limits("foldback_arm_bp", "loop_word"), partitions
    )
    # Both arms have a witness. Impossible earlier join positions must not make
    # the first 8-bp arm wait behind another sequence on a 6-bp arm.
    assert after.costs[4][1] == after.costs[4][4] == 0
    assert after.costs[4][5] == 1
    assert all(after.costs[4][i] > 1 for i in (0, 2, 3))
    assert set(after.at_most(after.maximum)) == set(before.at_most(before.maximum))


def test_admission_compaction_leaves_unknown_unexamined_and_unrequested_costs_alone():
    branches, before = case_order((0, 1, 2, 3))

    def population(i):
        if i == 2:
            raise SequenceSetLimitError("stopped local proof")
        return SimpleNamespace(parts=(0, 3)[i])

    limits = objective_limits("loop_word").model_copy(update={"navigation_nodes": 3})
    after = admitted_geometry_order(
        branches, limits, SimpleNamespace(foldback_population=population)
    )
    assert after.costs[4][1] == 0
    assert after.costs[4][2:] == before.costs[4][2:]
    limits = objective_limits("left_gap").model_copy(update={"navigation_nodes": 3})
    after = admitted_geometry_order(
        branches, limits, SimpleNamespace(foldback_population=population)
    )
    assert after.costs[4][1:] == before.costs[4][1:]


def test_known_empty_cases_follow_admitted_cases_but_remain_reachable():
    branches, before = case_order()
    partitions = SimpleNamespace(foldback_population=lambda i: SimpleNamespace(parts=(0, 5, 2)[i]))
    after = admitted_geometry_order(branches, objective_limits("loop_word"), partitions)
    assert after.costs[4][1] < after.costs[4][2] < after.costs[4][0]
    assert set(after.at_most(after.maximum)) == set(
        product(*(range(size) for size in branches.geometry_sizes))
    )
    assert before.costs[4] == (0, 1, 2)


def test_default_search_defers_proven_empty_cases_without_a_diversity_objective():
    branches, before = case_order()
    limits = objective_limits("loop_word").model_copy(update={"objective": None})
    partitions = SimpleNamespace(foldback_population=lambda i: SimpleNamespace(parts=(0, 5, 2)[i]))
    after = admitted_geometry_order(branches, limits, partitions)
    assert after.costs[4][1:] == before.costs[4][1:]
    assert after.costs[4][0] > max(after.costs[4][1:])
    assert set(after.at_most(after.maximum)) == set(before.at_most(before.maximum))


@pytest.mark.parametrize(
    "error",
    [
        SequenceSetLimitError("probe stopped"),
        ProductConstraintConflict(
            "representative basal conflict", code="test", position_from_ligation=0
        ),
    ],
)
def test_stopped_or_conflicting_probes_keep_ordinary_priority(error):
    branches, before = case_order()

    def unavailable(i):
        raise error

    after = admitted_geometry_order(
        branches, objective_limits("loop_word"), SimpleNamespace(foldback_population=unavailable)
    )
    assert after is before


def test_unexpected_admission_failure_is_not_silenced():
    branches, _ = case_order()

    def broken(i):
        raise ValueError("corrupt authority")

    with pytest.raises(ValueError, match="corrupt authority"):
        admitted_geometry_order(
            branches, objective_limits("loop_word"), SimpleNamespace(foldback_population=broken)
        )


@pytest.mark.parametrize("budget", [2, MAX_FOLDBACK_PROBES + 10])
def test_probe_has_a_fixed_cap_and_leaves_unexamined_values_unchanged(budget):
    branches, before = case_order(tuple(range(MAX_FOLDBACK_PROBES + 20)))
    visited = []

    def empty(i):
        visited.append(i)
        return SimpleNamespace(parts=0)

    limits = objective_limits("loop_word").model_copy(update={"navigation_nodes": budget})
    after = admitted_geometry_order(branches, limits, SimpleNamespace(foldback_population=empty))
    assert len(visited) == min(budget, MAX_FOLDBACK_PROBES)
    assert after.costs[4][len(visited) :] == before.costs[4][len(visited) :]


def test_all_word_search_keeps_its_existing_order():
    branches, before = case_order(context="all_words")
    assert (
        admitted_geometry_order(branches, objective_limits("loop_word"), SimpleNamespace())
        is before
    )


def test_invocation_reuses_one_order_and_rejects_other_dependencies(monkeypatch):
    import json

    from hop_design.design.construction.surveys.admission import locals as admission
    from hop_design.design.construction.surveys.branches import SurveyBranches
    from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
    from tests.unit.test_interface_survey_request import survey_document

    branches = SurveyBranches(
        InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    )
    limits = objective_limits("loop_word")
    calls = []

    def admitted(*args):
        calls.append(args)
        return branches.geometry_order

    monkeypatch.setattr(admission, "admitted_geometry_order", admitted)
    local = admission.LocalReceipts(SimpleNamespace(request=branches.request), limits)
    assert local.search_order(branches, limits) is local.search_order(branches, limits)
    assert len(calls) == 1
    with pytest.raises(ValueError, match="invocation"):
        local.search_order(branches, limits.model_copy(update={"navigation_nodes": 1}))
    different = SurveyBranches(branches.request.model_copy(update={"name": "another request"}))
    with pytest.raises(ValueError, match="invocation"):
        local.search_order(different, limits)
