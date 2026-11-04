"""An optional interface objective stays inside the unified design lifecycle."""

import json

import pytest

from hop_design import construction
from tests.integration.test_design_diversity import diverse_intent


def test_interface_diversity_preserves_permissions_exact_resume_replay_and_handoff(tmp_path):
    intent = diverse_intent()
    objective = {"kind": "diversity", "parameters": ["left_end_word", "right_end_word"]}
    first = construction.discover_designs(
        intent, tmp_path / "split", max_evaluations=8, objective=objective
    )
    original = first.query()
    continued = first.find_more(max_evaluations=8)
    whole = construction.discover_designs(
        intent, tmp_path / "whole", max_evaluations=16, objective=objective
    )
    assert continued.query() == whole.query()
    assert first.query() == original
    assert continued.resolution == first.resolution
    assert continued.resolution["intent"]["ends"] is None
    answer = continued.query()
    assert answer["search_objective"]["target_policy"] == "joint_interface_relations/v9"
    assert answer["search_objective"]["observed_classes"] >= 2
    selected = continued.sample(seed=4)
    receipt = continued.retrieve(selected, tmp_path / "materials")
    assert selected["materialized_realization_id"] in receipt.materialized_realization_ids
    assert construction.load_design_choices(tmp_path / "split").query() == answer
    replay = construction.verify_interface_survey(
        tmp_path / "split/intent/request.json", tmp_path / "split/survey.sqlite"
    )
    assert replay["replayed_evaluations"] == 16
    assert json.loads((tmp_path / "split/effort.json").read_text())["objective"] == objective


def test_interface_objective_on_hairpin_is_explained_before_creating_outputs(tmp_path):
    from tests.unit.test_construction_intent import STEM

    with pytest.raises(ValueError, match="not applicable"):
        construction.discover_designs(
            {"stem_arm": STEM, "product": "hairpin"},
            tmp_path / "absent",
            max_evaluations=1,
            objective={"kind": "diversity", "parameters": ["left_end_word"]},
        )
    assert not (tmp_path / "absent").exists()
