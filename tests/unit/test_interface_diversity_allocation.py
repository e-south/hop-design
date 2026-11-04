"""Interface exploration proposes joint targets without pruning the search domain."""

import json

import pytest

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.completion.interfaces import EndPairRelations
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.construction.surveys.targets import InterfaceTargetDomain
from tests.unit.test_design_diversity import objective_limits
from tests.unit.test_interface_survey_request import survey_document


def branches_with_targets():
    data = survey_document()
    data["source_context_objective"] = "paired_scaffold_completions"
    data["targets"] = {"left_words": ["AAAA", "CCCC"], "right_words": ["GGGG", "TTTT"]}
    return SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(data)))


def relation(*words):
    builder = SequenceSetBuilder(length_nt=8, max_nodes=1000, max_operations=10000)
    node = 0
    for word in words:
        node = builder.union(node, builder.from_iupac(word))
    return builder.freeze(node)


def test_end_words_are_supported_diversity_dimensions():
    policy = objective_limits("left_end_word", "right_end_word").objective
    assert policy.parameters == ("left_end_word", "right_end_word")


def test_objective_policy_versions_cross_target_class_preferences():
    assert objective_limits("left_gap").objective.target_policy == "joint_interface_relations/v9"


def test_seed_classes_retain_the_joint_geometry_where_a_pair_was_admitted(monkeypatch):
    from hop_design.design.construction.search.diversity import diversity_class
    from hop_design.design.construction.surveys.navigation.target_seeds import (
        propose_interface_targets,
    )

    def admitted(self, product):
        return relation("AAAATTTT" if product.ends.left.payload_end_offset_bp == 6 else "CCCCGGGG")

    monkeypatch.setattr(EndPairRelations, "relation", admitted)
    branches = branches_with_targets()
    limits = objective_limits("left_gap", "right_gap")
    seeds = propose_interface_targets(branches, limits)
    by_pair = {branches.request.targets.pair_at(t): c for t, c in seeds.candidate_classes.items()}
    assert by_pair == {
        ("AAAA", "TTTT"): frozenset(
            {diversity_class(limits.objective, {"left_gap": 6, "right_gap": 6})}
        ),
        ("CCCC", "GGGG"): frozenset(
            {diversity_class(limits.objective, {"left_gap": 0, "right_gap": 0})}
        ),
    }


def test_unknown_loop_sequence_does_not_create_an_achievable_seed_class(monkeypatch):
    from hop_design.design.construction.surveys.navigation.target_seeds import (
        propose_interface_targets,
    )

    monkeypatch.setattr(EndPairRelations, "relation", lambda self, product: relation("AAAATTTT"))
    branches = branches_with_targets()
    assert all(c.loop_sequence is None for c in branches.foldback_cases)
    seeds = propose_interface_targets(branches, objective_limits("left_gap", "loop_word"))
    assert seeds.targets and not seeds.candidate_classes


def test_proposals_intersect_joint_relations_and_request_without_cross_combinations(monkeypatch):
    from hop_design.design.construction.surveys.navigation.target_seeds import (
        propose_interface_targets,
    )

    possible = relation("AAAATTTT", "CCCCGGGG", "AAAAACGT")
    monkeypatch.setattr(EndPairRelations, "relation", lambda self, product: possible)
    branches = branches_with_targets()
    original = branches.request.model_dump(mode="json")
    seeds = propose_interface_targets(branches, objective_limits("left_gap"))
    assert {branches.request.targets.pair_at(t) for t in seeds.targets} == {
        ("AAAA", "TTTT"),
        ("CCCC", "GGGG"),
    }
    assert branches.request.model_dump(mode="json") == original


def test_unknown_or_resource_stopped_relations_never_become_target_exclusions(monkeypatch):
    from hop_design.design.construction.surveys.navigation.target_seeds import (
        propose_interface_targets,
    )

    monkeypatch.setattr(EndPairRelations, "relation", lambda self, product: None)
    branches = branches_with_targets()
    seeds = propose_interface_targets(branches, objective_limits("right_gap"))
    assert seeds.targets == () and seeds.unknown_frames > 0

    def stopped(self, product):
        raise SequenceSetLimitError("probe budget")

    monkeypatch.setattr(EndPairRelations, "relation", stopped)
    seeds = propose_interface_targets(branches, objective_limits("right_gap"))
    assert seeds.targets == () and seeds.resource_stopped
    assert branches.request.targets.pair_count == 4


def test_seed_work_is_bounded_by_navigation_budget(monkeypatch):
    from hop_design.design.construction.surveys.navigation.target_seeds import (
        propose_interface_targets,
    )

    calls = []
    possible = relation("AAAATTTT")

    def inspect(self, product):
        calls.append(product)
        return possible

    monkeypatch.setattr(EndPairRelations, "relation", inspect)
    limits = objective_limits("left_gap").model_copy(update={"navigation_nodes": 3})
    seeds = propose_interface_targets(branches_with_targets(), limits)
    assert seeds.examined_frames == len(calls) == 3
    assert len({p.ends.left.payload_end_offset_bp for p in calls}) == 2


def test_seeded_schedule_prioritizes_suggestions_preserves_fallback_and_resumes():
    from hop_design.design.construction.surveys.schedule import InterfaceDiversitySchedule

    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    last, supported = {}, set()
    schedule = InterfaceDiversitySchedule(
        domain, last=last, ended=set(), supported=supported, preferred=(3,)
    )
    visits = []
    for _ in range(512):
        rebuilt = InterfaceDiversitySchedule(
            domain, last=last, ended=set(), supported=supported, preferred=(3,)
        )
        target = schedule.pop()
        assert target == rebuilt.pop()
        visits.append(target)
        last[target] = last.get(target, -1) + 1
        supported.add(target)
        schedule.update(target, step=last[target], supported=True, ended=False)
    assert visits[:2] == [3, 0]
    assert set(visits) == {0, 1, 2, 3}
    assert min(last.values()) > 1


@pytest.mark.parametrize("preferred", [(4,), (-1,), (True,), (0, 0)])
def test_seeded_schedule_rejects_invalid_or_repeated_targets(preferred):
    from hop_design.design.construction.surveys.schedule import InterfaceDiversitySchedule

    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    with pytest.raises(ValueError, match="target"):
        InterfaceDiversitySchedule(
            domain, last={}, ended=set(), supported=set(), preferred=preferred
        )


def test_bounded_seed_probe_reaches_each_basal_factor_before_lexicographic_repeats(monkeypatch):
    from types import SimpleNamespace

    from hop_design.design.construction.surveys.coordinates import coordinate_at
    from hop_design.design.construction.surveys.navigation.target_seeds import (
        propose_interface_targets,
    )

    base = branches_with_targets()
    sizes = (1, 3, 4, 2, 1, 2)
    visited = []

    def candidate(target, *, branch, limits):
        assert target == 0
        visited.append(coordinate_at(sizes, branch))
        return object()

    # This seam observes frame allocation, without pretending a frame is a molecule.
    branches = SimpleNamespace(
        request=base.request,
        placements=base.placements[:1],
        geometry_sizes=sizes,
        product=candidate,
    )
    monkeypatch.setattr(EndPairRelations, "relation", lambda self, product: None)
    seeds = propose_interface_targets(branches, objective_limits("left_end_word"))
    assert seeds.examined_frames == seeds.unknown_frames == len(visited) == 16
    assert seeds.targets == () and not seeds.resource_stopped
    for dimension in (1, 2, 3, 5):
        assert {g[dimension] for g in visited} == set(range(sizes[dimension]))
    assert len(set(visited)) == len(visited)


@pytest.mark.parametrize("sizes", [(3, 4, 2, 2), (1, 1, 1, 1), (2, 3, 1, 4)])
def test_seed_order_retains_every_original_frame_once(sizes):
    from itertools import product

    from hop_design.design.construction.surveys.navigation.target_seeds import _seed_frames

    frames = list(_seed_frames(sizes))
    expected = set(product(*(range(size) for size in sizes)))
    assert set(frames) == expected
    assert len(frames) == len(expected)


def test_seed_order_does_not_materialize_a_large_cartesian_domain():
    from itertools import islice

    from hop_design.design.construction.surveys.navigation.target_seeds import _seed_frames

    frames = list(islice(_seed_frames((10**9,) * 4), 16))
    assert len(frames) == len(set(frames)) == 16


def test_constraint_derived_targets_precede_unexamined_canonical_fallback():
    from hop_design.design.construction.surveys.schedule import InterfaceDiversitySchedule

    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    schedule = InterfaceDiversitySchedule(
        domain, last={}, ended=set(), supported=set(), preferred=(3,)
    )
    # A necessary molecular relation supplied target 3. Nothing supplied an
    # equivalent reason to spend the first construction turn on target 0.
    assert schedule.pop() == 3


def test_exhausted_seed_does_not_remove_unknown_targets_from_the_domain():
    from hop_design.design.construction.surveys.schedule import InterfaceDiversitySchedule

    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    schedule = InterfaceDiversitySchedule(
        domain, last={}, ended=set(), supported=set(), preferred=(3,)
    )
    assert schedule.pop() == 3
    schedule.update(3, step=0, supported=False, ended=True)
    remainder = []
    while (target := schedule.pop()) is not None:
        remainder.append(target)
        schedule.update(target, step=0, supported=False, ended=True)
    assert sorted(remainder) == [0, 1, 2]


def test_explicit_preparation_preference_precedes_inferred_target_suggestions():
    from hop_design.design.construction.surveys.schedule import InterfaceDiversitySchedule

    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    schedule = InterfaceDiversitySchedule(
        domain, last={}, ended=set(), supported=set(), preferred=(3,)
    )
    schedule.prefer_next(0)
    assert schedule.pop() == 0
    schedule.update(0, step=0, supported=False, ended=False)
    assert schedule.pop() == 3
