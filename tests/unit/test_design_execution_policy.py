"""Execution policy errors precede filesystem publication or molecular search."""

import pytest

from hop_design import construction
from tests.unit.test_construction_intent import STEM


@pytest.mark.parametrize(
    "product,first", [("hairpin", True), ("hairpin", 0), ("released_insert", 1)]
)
def test_invalid_first_choice_policy_does_not_create_a_discovery(product, first, tmp_path):
    output = tmp_path / "designs"
    with pytest.raises(ValueError, match=r"[Ff]irst.choice"):
        construction.discover_designs(
            {"stem_arm": STEM, "product": product}, output, first_choices=first
        )
    assert not output.exists()


def test_saved_first_choice_policy_must_agree_with_examined_outcomes():
    from hop_design.design.construction.intents.hairpin_history import validate_execution
    from hop_design.models.construction.intents.execution import HairpinExecution

    execution = HairpinExecution(
        max_evaluations=4,
        first_choices=1,
        previous_evaluated_pairs=0,
        evaluated_pairs=2,
        snapshot_digest="sha256:" + "1" * 64,
        stopping_reason="first_choices",
    )
    options = {
        "coverage": {"recorded_pairs": 6, "evaluated_pairs": 2, "unexamined_pairs": 4},
        "candidates": [{"outcome": f"candidates/{i:04d}/outcome/report.md"} for i in range(2)],
        "options": [{"selection": {"bundle_path": "candidates/0001/outcome/construction"}}],
    }
    validate_execution(execution, options)
    with pytest.raises(ValueError, match="stopping"):
        validate_execution(execution.model_copy(update={"first_choices": 2}), options)
    with pytest.raises(ValueError, match="stopping"):
        validate_execution(
            execution.model_copy(update={"stopping_reason": "evaluation_limit"}), options
        )
    # A completed preparation in the first attempt should have stopped sooner.
    options["options"][0]["selection"]["bundle_path"] = "candidates/0000/outcome/construction"
    with pytest.raises(ValueError, match="stopping"):
        validate_execution(execution, options)


def test_paged_hairpin_policy_can_cross_64_without_resetting_candidate_addresses():
    from hop_design.design.construction.intents.hairpin_history import validate_execution
    from hop_design.models.construction.intents.execution import HairpinExecution

    execution = HairpinExecution(
        schema="hop.hairpin-design-execution/v2",
        max_evaluations=2,
        previous_evaluated_pairs=64,
        evaluated_pairs=66,
        previous_snapshot_digest="sha256:" + "0" * 64,
        snapshot_digest="sha256:" + "1" * 64,
        stopping_reason="evaluation_limit",
    )
    options = {
        "pair_window": {"start": 64, "stop": 66},
        "coverage": {"recorded_pairs": 80, "evaluated_pairs": 2},
        "candidates": [{"outcome": f"candidates/{i:04d}/outcome/report.md"} for i in (64, 65)],
        "options": [],
    }
    validate_execution(execution, options)
    options["pair_window"]["start"] = 63
    with pytest.raises(ValueError, match="contiguous"):
        validate_execution(execution, options)


def test_hairpin_entry_continues_after_64_recorded_attempts(tmp_path, monkeypatch):
    import json

    from hop_design.design.construction.intents import hairpins

    previous = tmp_path / "previous"
    (previous / "branches/0000").mkdir(parents=True)
    (previous / "summary.json").write_text(json.dumps({"coverage": {"evaluated_pairs": 64}}))
    (previous / "branches/0000/summary.json").write_text(
        json.dumps({"coverage": {"recorded_pairs": 80}})
    )
    (previous / "manifest.json").write_text("{}")
    (tmp_path / "effort.json").write_text(
        json.dumps({"local_nodes": 1000, "local_realizations": 1000})
    )
    monkeypatch.setattr(hairpins, "snapshot_paths", lambda root: [previous])
    monkeypatch.setattr(hairpins, "snapshot_source", lambda root: (previous, None))

    class ReachedNextPage(Exception):
        pass

    def observe(path, **kwargs):
        assert kwargs["start_pair"] == 64
        assert kwargs["local_source"] == previous / "branches/0000"
        assert json.loads(path.read_bytes())["max_continuations_per_branch"] == 4
        raise ReachedNextPage

    monkeypatch.setattr(hairpins, "_discover_with_receipts", observe)
    resolution = construction.resolve_design_request(
        {"stem_arm": STEM, "product": "hairpin"}
    ).json_bytes
    with pytest.raises(ReachedNextPage):
        hairpins.evaluate_hairpins(tmp_path, 4, resolution=resolution)


def test_cli_first_choices_delegates_the_same_explicit_execution_policy(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from typer.testing import CliRunner

    from hop_design.cli import app

    calls = []

    def discover(request, destination, **kwargs):
        calls.append((request, destination, kwargs))
        return SimpleNamespace(query=lambda query=None: {"recorded": True})

    monkeypatch.setattr(construction, "discover_designs", discover)
    result = CliRunner().invoke(
        app,
        [
            "design",
            "discover",
            "--stem",
            STEM,
            "--product",
            "hairpin",
            "--out",
            str(tmp_path / "hairpins"),
            "--evaluations",
            "4",
            "--first-choices",
            "1",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert calls[0][2] == {"max_evaluations": 4, "first_choices": 1, "objective": None}


def test_cli_diversity_uses_the_same_search_objective(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from typer.testing import CliRunner

    from hop_design.cli import app

    calls = []

    def discover(request, destination, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(query=lambda query=None: {"recorded": True})

    monkeypatch.setattr(construction, "discover_designs", discover)
    result = CliRunner().invoke(
        app,
        [
            "design",
            "discover",
            "--stem",
            STEM,
            "--product",
            "released_insert",
            "--out",
            str(tmp_path / "choices"),
            "--diversify",
            "loop_nt",
            "--diversify",
            "foldback_arm_bp",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert calls[0]["objective"] == {
        "kind": "diversity",
        "parameters": ["loop_nt", "foldback_arm_bp"],
    }
