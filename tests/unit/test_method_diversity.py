"""Nickase objectives use role identities, not entire enzyme rosters or extra words."""

import json
from dataclasses import replace

import pytest

from hop_design.design.construction.local_choices import (
    LocalRealizationChoice,
    list_local_realizations,
)
from hop_design.design.construction.local_public import _discover_request
from hop_design.design.construction.options.order import (
    ordered_pairs,
    validate_options_objective,
)
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.construction.targets import BasalTarget, FoldbackTarget
from hop_design.models.junction import Strand
from tests.unit.test_design_diversity import objective_limits
from tests.unit.test_interface_survey_compact_foldback import _two_method_product
from tests.unit.test_interface_survey_request import survey_document


def test_method_objectives_have_separate_policies_without_changing_existing_objectives():
    assert objective_limits("foldback_method").objective.target_policy == "within_target/v6"
    assert (
        objective_limits("basal_method", "loop_word").objective.target_policy == "within_target/v6"
    )
    assert (
        objective_limits("basal_method", "left_gap").objective.target_policy
        == "joint_interface_relations/v9"
    )
    assert objective_limits("loop_word").objective.target_policy == "within_target/v5"
    assert objective_limits("release_method").objective.target_policy == "within_target/v2"


@pytest.mark.parametrize("dimension", ["foldback_method", "basal_method"])
def test_method_objectives_require_the_feedback_capable_survey_mode(dimension):
    document = survey_document()
    document["source_context_objective"] = "all_words"
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    with pytest.raises(ValueError, match="paired_scaffold_completions"):
        branches.search_order(objective_limits(dimension))
    document["source_context_objective"] = "paired_scaffold_completions"
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    assert (
        tuple(map(len, branches.search_order(objective_limits(dimension)).costs))
        == branches.geometry_sizes
    )


def test_basal_method_is_inapplicable_to_direct_hairpin_options():
    from hop_design import construction
    from tests.unit.test_construction_intent import STEM

    resolved = json.loads(
        construction.resolve_design_request({"stem_arm": STEM, "product": "hairpin"}).json_bytes
    )
    request = ProductRequest.model_validate_json(json.dumps(resolved["effective_request"]))
    with pytest.raises(ValueError, match="no basal association"):
        validate_options_objective(request, objective_limits("basal_method").objective)
    validate_options_objective(request, objective_limits("foldback_method").objective)


def _choice(label, *, basal=False, method="example:enzyme/a@1", additional="example:enzyme/x@1"):
    geometry = (
        BasalTarget(nick_strand=Strand.BOTTOM, nick_offset_nt=0)
        if basal
        else FoldbackTarget(junction_offset_nt=0, loop_length_nt=4, annealing_arm_length_bp=6)
    )
    return LocalRealizationChoice(
        source_result_id="inspection",
        realization_id=label,
        geometry=geometry,
        retained_overhead_nt=16,
        enzyme_ids=(method, additional),
        cohesive_end=None,
        pairing_classes=(),
        required_annealing_nt=10 if basal else None,
        annealing_completion_nt=10 if basal else None,
        material_requirements=(),
        nick_enzyme_id=method,
    )


@pytest.mark.parametrize("family", ["foldback", "basal"])
def test_local_method_order_ignores_other_enzyme_roles_and_preserves_all_pairs(family):
    first = _choice("first", basal=family == "basal")
    repeat = replace(
        first,
        realization_id="other-release-or-terminus",
        enzyme_ids=(first.nick_enzyme_id, "example:enzyme/y@1"),
    )
    alternative = _choice("new-nickase", basal=family == "basal", method="example:enzyme/b@1")
    choices = {"foldback": (_choice("fixed"),), family: (first, repeat, alternative)}
    ordered = list(ordered_pairs(choices, objective_limits(f"{family}_method").objective))
    index = 0 if family == "foldback" else 1
    assert [pair[index].realization_id for pair in ordered] == [
        "first",
        "new-nickase",
        "other-release-or-terminus",
    ]
    assert (
        len(
            {
                tuple(None if part is None else part.realization_id for part in pair)
                for pair in ordered
            }
        )
        == 3
    )


@pytest.fixture(scope="module")
def admitted():
    product = _two_method_product()
    parts = PartitionPlans().get(product)
    assert parts.foldback is not None and parts.basal_candidates is not None
    return product, parts


def test_population_method_lookup_does_not_expand_or_unrank_sequences(admitted, monkeypatch):
    from hop_design.models.construction.sequence_sets import SequenceSet

    _, parts = admitted

    def unexpected(*args, **kwargs):
        raise AssertionError("Method lookup must not materialize a sequence member.")

    monkeypatch.setattr(SequenceSet, "member_at", unexpected)
    for kind in {type(support) for support in parts.basal_candidates.supports}:
        monkeypatch.setattr(kind, "member_at", unexpected)
    methods = {parts.foldback.method_at(rank) for rank in range(2)}
    assert methods == {"example:enzyme/nt.bpu10i@1", "example:enzyme/nb.bsrdi@1"}
    assert parts.basal_candidates.method_at(0) == "example:enzyme/nb.bsrdi@1"
    assert (
        parts.basal_candidates.method_at(parts.basal_candidates.parts - 1)
        == "example:enzyme/nb.bsrdi@1"
    )
    for population in (parts.foldback, parts.basal_candidates):
        with pytest.raises(ValueError, match="address"):
            population.method_at(population.parts)


@pytest.mark.parametrize("family", ["foldback", "basal"])
def test_population_and_local_inspection_method_match_replayed_role(admitted, family):
    product, parts = admitted
    population = parts.foldback if family == "foldback" else parts.basal_candidates
    for rank in (0, population.parts - 1):
        selected = population.select(product, rank)
        receipt = _discover_request(getattr(selected.construction_source(), family))
        records = json.loads(receipt.json_bytes)["realizations"]
        assert len(records) == 1
        method = records[0][f"{family}_nick"]["enzyme_id"]
        assert population.method_at(rank) == method
        assert list_local_realizations(receipt)[0].nick_enzyme_id == method


def test_page_coordinates_use_nickase_roles_not_provisioned_method_sets(admitted):
    from hop_design.design.construction.surveys.navigation.diversity import (
        local_page_values,
    )

    _, parts = admitted
    values = [
        local_page_values(parts, page, ("foldback_method", "basal_method")) for page in range(3)
    ]
    assert {row["foldback_method"] for row in values} == {
        "example:enzyme/nt.bpu10i@1",
        "example:enzyme/nb.bsrdi@1",
    }
    assert {row["basal_method"] for row in values} == {"example:enzyme/nb.bsrdi@1"}
    assert all(isinstance(value, str) for row in values for value in row.values())


def test_real_method_feedback_prioritizes_a_new_program_and_cold_resume_keeps_every_page(admitted):
    from hop_design.design.construction.search.diversity import allocation_classes
    from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
    from hop_design.design.construction.surveys.coordinates import coordinate_rank
    from hop_design.design.construction.surveys.geometry_order import GeometryOrder
    from hop_design.design.construction.surveys.navigation.diversity import local_page_values
    from hop_design.models.construction.surveys.completion import CompletionSeekCursor

    _, parts = admitted
    sizes = (parts.foldback.parts, parts.basal_candidates.parts)
    pages = tuple(sorted(coordinate_rank(sizes, pair) for pair in ((0, 0), (0, 1), (1, 0))))
    objective = objective_limits("foldback_method").objective
    first_method = parts.foldback.method_at(0)
    known = allocation_classes(objective, {"foldback_method": first_method})

    def class_key(geometry, page):
        if page is None:
            return (None,)
        return allocation_classes(objective, local_page_values(parts, page, objective.parameters))

    navigator = CompletionNavigator(
        GeometryOrder(tuple((0,) for _ in range(6))),
        lambda geometry, depth, after: (p for p in pages if p > after) if depth == 0 else iter(()),
        lambda geometry, page: 1,
        class_key=class_key,
    )
    cursor = CompletionSeekCursor(schema="hop.context-group-seek/v7", observed_classes=known)
    visited = []
    while cursor is not None:
        result = navigator.scan(cursor, empty_planes=frozenset(), maximum_nodes=1)
        if result.address is not None:
            visited.append(result.address[1])
        cursor = result.cursor
        if cursor is not None:
            cursor = CompletionSeekCursor.model_validate_json(cursor.model_dump_json())
    assert (
        local_page_values(parts, visited[0], objective.parameters)["foldback_method"]
        != first_method
    )
    assert len(visited) == len(pages) and set(visited) == set(pages)
