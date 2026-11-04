"""Useful contrasts are complete compiler witnesses in the shared design lifecycle."""

import json

import pytest

from hop_design import construction
from tests.integration.test_design_discovery import intent_document


def diverse_intent():
    intent = intent_document()
    context = intent["context"]
    context["source_context_objective"] = "paired_scaffold_completions"
    context["foldback"]["geometry"].update(loop_lengths_nt=[4, 5, 6], annealing_arm_lengths_bp=[7])
    context["foldback"]["max_retained_overhead_nt"] = 20
    return intent


def test_objective_reaches_loop_contrasts_without_requiring_ends(tmp_path):
    from hop_design.design.construction.search.diversity import diversity_class
    from hop_design.models.construction.variants.objective import DesignSearchObjective
    from tests.support.context_completion import records

    objective = {"kind": "diversity", "parameters": ["loop_nt"]}
    output = tmp_path / "diverse"
    choices = construction.discover_designs(
        diverse_intent(), output, max_evaluations=16, objective=objective
    )
    answer = choices.query()
    assert {path["values"]["loop_nt"] for path in answer["paths"]} >= {4, 5}
    assert answer["search_objective"]["observed_classes"] >= 2
    assert choices.resolution["intent"]["ends"] is None
    assert json.loads((output / "effort.json").read_bytes())["objective"] == objective
    selected = choices.sample(seed=1)
    retrieved = choices.retrieve(selected, tmp_path / "preparation")
    assert selected["materialized_realization_id"] in retrieved.materialized_realization_ids
    loaded = construction.load_design_choices(output)
    assert loaded.query() == answer
    policy = DesignSearchObjective.model_validate_json(json.dumps(objective))
    observed_by_target = {}
    for record in records(output / "survey.sqlite"):
        target = record["target"]
        seen = observed_by_target.setdefault(target, set())
        seen.update(diversity_class(policy, p["values"]) for p in record["projections"])
        following = record.get("next") or {}
        cursor = following.get("completion_seek", following.get("completion", {}).get("after"))
        if cursor is not None:
            assert cursor["schema"] == "hop.context-group-seek/v7"
            assert set(cursor.get("observed_classes", ())) == seen
    assert any(observed_by_target.values())


@pytest.mark.parametrize("dimension", ["loop_nt", "loop_word"])
def test_diversity_resume_matches_equal_uninterrupted_work_and_replays(tmp_path, dimension):
    objective = {"kind": "diversity", "parameters": [dimension]}
    first = construction.discover_designs(
        diverse_intent(), tmp_path / "split", max_evaluations=4, objective=objective
    )
    original = first.query()
    resumed = first.find_more(max_evaluations=4)
    whole = construction.discover_designs(
        diverse_intent(), tmp_path / "whole", max_evaluations=8, objective=objective
    )
    assert resumed.query() == whole.query()
    assert first.query() == original
    replay = construction.verify_interface_survey(
        tmp_path / "split/intent/request.json", tmp_path / "split/survey.sqlite"
    )
    assert replay["replayed_evaluations"] == 8


def test_diversity_more_scaffold_classes_at_the_same_budget(tmp_path):
    current = construction.discover_designs(
        diverse_intent(), tmp_path / "current", max_evaluations=16
    ).query()
    diverse = construction.discover_designs(
        diverse_intent(),
        tmp_path / "diverse",
        max_evaluations=16,
        objective={"kind": "diversity", "parameters": ["loop_nt"]},
    ).query()
    assert {p["values"]["loop_nt"] for p in diverse["paths"]} == {4, 5, 6}
    assert len({p["values"]["loop_nt"] for p in current["paths"]}) < 3
    assert diverse["coverage"]["unexamined_pairs"] > 0


@pytest.mark.parametrize("product", ["hairpin", "adapter_ligated_hairpin"])
@pytest.mark.parametrize("dimension", ["loop_nt", "loop_word"])
def test_hairpin_objective_uses_same_lifecycle_and_preserves_resume_order(
    product, dimension, tmp_path
):
    from tests.unit.test_construction_intent import STEM

    intent = {"stem_arm": STEM, "product": product}
    context = json.loads(construction.resolve_design_request(intent).json_bytes)["permissions"]
    context["foldback"]["geometry"].update(annealing_arm_lengths_bp=[7], loop_lengths_nt=[4, 5, 6])
    context["foldback"]["max_retained_overhead_nt"] = 20
    request = {**intent, "context": context}
    objective = {"kind": "diversity", "parameters": [dimension]}
    effort = {"local_nodes": 1000, "local_realizations": 32, "release_site_pairs": 1000}
    first = construction.discover_designs(
        request, tmp_path / "split", max_evaluations=2, objective=objective, effort=effort
    )
    original = first.query()
    continued = construction.continue_design_discovery(tmp_path / "split", max_evaluations=2)
    full = construction.discover_designs(
        request, tmp_path / "full", max_evaluations=4, objective=objective, effort=effort
    )
    assert continued.query()["paths"] == full.query()["paths"]
    assert continued.query()["search_objective"]["observed_classes"] >= 2
    assert len({path["values"][dimension] for path in continued.query()["paths"]}) >= 2
    assert first.query() == original
    assert construction.load_design_choices(tmp_path / "split").query() == continued.query()
    selected = continued.sample(seed=0)
    receipt = continued.retrieve(selected, tmp_path / "materials")
    assert selected["materialized_realization_id"] in receipt.materialized_realization_ids
