"""Resource exhaustion stops automation without discarding committed choices."""

import sqlite3

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.design.construction.surveys import execute
from hop_design.design.construction.surveys.completion.navigation import (
    CompletionFrontierLimitError,
)
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from tests.integration.test_design_discovery import intent_document


def test_sequence_budget_is_visible_from_the_simple_discovery_api(tmp_path):
    root = tmp_path / "choices"
    intent = {**intent_document(), "ends": {"left": "AGTC", "right": "AGTC"}}
    with pytest.raises(ValueError, match="sequence_space_budget"):
        construction.discover_designs(
            intent,
            root,
            max_evaluations=1,
            effort={
                "local_nodes": 100,
                "local_realizations": 100,
                "release_site_pairs": 100,
                "sequence_decisions": 1,
            },
        )
    saved = construction.load_design_choices(root).query()
    assert saved["coverage"]["unresolved_pairs"] == 1
    assert saved["coverage"]["excluded_pairs"] == 0


@pytest.mark.parametrize(
    "reason", ["sequence_space_budget", "navigation_frontier_budget", "checkpoint_storage_limit"]
)
def test_resource_stop_preserves_choices_and_stops_cli_automation(tmp_path, monkeypatch, reason):
    root = tmp_path / "choices"
    before = construction.discover_designs(intent_document(), root, max_evaluations=1).query()
    assert before["matching_preparations"] > 0

    def resource_stop(*args, **kwargs):
        if reason == "sequence_space_budget":
            raise SequenceSetLimitError("injected bounded resource failure")
        if reason == "navigation_frontier_budget":
            raise CompletionFrontierLimitError("injected bounded resource failure")
        error = sqlite3.OperationalError("database or disk is full")
        error.sqlite_errorcode = sqlite3.SQLITE_FULL
        raise error

    with monkeypatch.context() as patch:
        patch.setattr(execute, "evaluate_step", resource_stop)
        with pytest.raises(ValueError, match=reason):
            construction.continue_design_discovery(root, max_evaluations=2)
        cli = CliRunner().invoke(app, ["design", "continue", str(root), "--evaluations", "2"])
        assert cli.exit_code != 0
        assert reason in cli.output
    assert construction.load_design_choices(root).query() == before
    assert (
        construction.verify_interface_survey(root / "intent/request.json", root / "survey.sqlite")[
            "replayed_evaluations"
        ]
        == 1
    )
    after = construction.continue_design_discovery(root, max_evaluations=1).query()
    assert after["snapshot_digest"] != before["snapshot_digest"]
