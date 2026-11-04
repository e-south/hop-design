"""Sequence exploration does not require the user to prescribe loop words."""

from hop_design import construction
from tests.integration.test_design_diversity import diverse_intent


def test_coupled_diversity_reaches_preparation_before_repeating_empty_foldbacks(tmp_path):
    request = diverse_intent()
    context = request["context"]
    context["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[6, 7, 8],
        junction_offsets_nt=[0, 1, 2],
        loop_lengths_nt=[3, 4, 5, 6],
    )
    context["foldback"]["max_retained_overhead_nt"] = 32
    context["basal"]["geometry"]["nick_offsets_nt"] = [0, 1, 2]
    context["basal"]["annealing_lengths_nt"] = [14, 17, 20, 24]
    objective = {
        "kind": "diversity",
        "parameters": [
            "foldback_arm_bp",
            "loop_word",
            "basal_nick_offset_nt",
            "adapter_annealing_min_nt",
            "release_method",
            "left_end_word",
            "right_end_word",
        ],
    }
    choices = construction.discover_designs(
        request, tmp_path / "choices", max_evaluations=8, objective=objective
    )
    assert choices.query()["paths"], "Proven-empty foldbacks must not consume the opening batch."
    assert choices.resolution["intent"]["ends"] is None
    selected = choices.sample(seed=1)
    preparation = choices.retrieve(selected, tmp_path / "preparation")
    assert selected["materialized_realization_id"] in preparation.materialized_realization_ids


def test_open_loop_word_objective_preserves_permissions_resume_and_handoff(tmp_path):
    request = diverse_intent()
    assert not request["context"]["foldback"]["geometry"].get("loop_sequences")
    objective = {"kind": "diversity", "parameters": ["loop_word"]}
    first = construction.discover_designs(
        request, tmp_path / "split", max_evaluations=8, objective=objective
    )
    original = first.query()
    continued = first.find_more(max_evaluations=8)
    complete = construction.discover_designs(
        request, tmp_path / "whole", max_evaluations=16, objective=objective
    )
    assert continued.query() == complete.query()
    assert first.query() == original
    assert continued.query()["search_objective"]["observed_classes"] >= 2
    assert len({p["values"]["loop_word"] for p in continued.query()["paths"]}) >= 2
    assert {len(p["values"]["loop_word"]) for p in continued.query()["paths"]} == {4, 5, 6}
    assert construction.load_design_choices(tmp_path / "split").query() == continued.query()
    selected = continued.sample(seed=1)
    receipt = continued.retrieve(selected, tmp_path / "materials")
    assert selected["materialized_realization_id"] in receipt.materialized_realization_ids
    replay = construction.verify_interface_survey(
        tmp_path / "split/intent/request.json", tmp_path / "split/survey.sqlite"
    )
    assert replay["replayed_evaluations"] == 16
