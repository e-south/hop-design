"""A reviewed permission edit executes into a new, portable discovery."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.integration.test_design_discovery import intent_document


def revision_intent():
    request = intent_document()
    request["context"]["foldback"]["max_retained_overhead_nt"] = 20
    return request


def test_revised_choices_preserve_parent_and_retrieve_after_relocation(tmp_path):
    parent = construction.discover_designs(
        revision_intent(), tmp_path / "parent", max_evaluations=1
    )
    original = parent.query()
    preview = parent.revise({"parameters": [{"key": "foldback_arm_bp", "values": [7]}]})
    revised = preview.execute(tmp_path / "revised", max_evaluations=1)
    assert parent.query() == original
    assert revised.query()["matching_preparations"] >= 1
    assert revised.resolution["intent"]["stem_arm"] == parent.resolution["intent"]["stem_arm"]
    assert (tmp_path / "revised/revision/parent.json").exists()
    shutil.copytree(tmp_path / "revised", tmp_path / "relocated")
    moved = construction.load_design_choices(tmp_path / "relocated")
    assert moved.query() == revised.query()
    selected = moved.sample(seed=1)
    receipt = moved.retrieve(selected, tmp_path / "preparation")
    assert selected["materialized_realization_id"] in receipt.materialized_realization_ids


def test_cli_previews_then_executes_the_same_revision(tmp_path):
    request = tmp_path / "intent.json"
    request.write_text(json.dumps(revision_intent()))
    changes = tmp_path / "changes.json"
    changes.write_text(json.dumps({"parameters": [{"key": "foldback_arm_bp", "values": [7]}]}))
    preview = tmp_path / "preview"
    runner = CliRunner()
    first = runner.invoke(
        app,
        [
            "design",
            "revise",
            "--request",
            str(request),
            "--changes",
            str(changes),
            "--out",
            str(preview),
            "--format",
            "text",
        ],
    )
    assert first.exit_code == 0, first.output
    assert "6" in first.output and "7" in first.output
    output = tmp_path / "choices"
    second = runner.invoke(
        app,
        [
            "design",
            "discover",
            "--revision",
            str(preview),
            "--out",
            str(output),
            "--evaluations",
            "1",
            "--format",
            "json",
        ],
    )
    assert second.exit_code == 0, second.output
    assert json.loads(second.output)["matching_preparations"] >= 1


def test_corrupt_revision_is_rejected_before_continuation_writes(tmp_path):
    preview = construction.preview_design_revision(
        revision_intent(), {"parameters": [{"key": "foldback_arm_bp", "values": [7]}]}
    )
    root = tmp_path / "choices"
    preview.execute(root, max_evaluations=1)
    index = root / "survey.sqlite"
    before = index.read_bytes()
    (root / "revision/request.json").write_text("{}")
    with pytest.raises(ValueError):
        construction.continue_design_discovery(root, max_evaluations=1)
    assert index.read_bytes() == before
