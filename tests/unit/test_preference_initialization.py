"""A failed reference import never publishes an incomplete survey checkpoint."""

import json
import random
import sqlite3

import pytest

from hop_design.design.construction.surveys.execute import evaluate_interface_survey
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import sha256_digest
from tests.unit.test_interface_survey_request import survey_document


def inputs(tmp_path, *, large=False):
    files = {"construction-bundle.json": b"{}", "authority.json": b'{"input":true}'}
    if large:
        files["authority.json"] = random.Random(42).randbytes(1_048_576)
    data = survey_document()
    data.update(
        source_context_objective="paired_scaffold_completions",
        preferred_preparation={
            "result_id": "hop:construction-space/" + "1" * 64 + "@1",
            "materialized_realization_id": "hop:materialized-construction/" + "2" * 64 + "@1",
            "files": [
                {
                    "path": name,
                    "digest": sha256_digest(raw),
                    "size_bytes": len(raw),
                    "media_type": "application/json",
                }
                for name, raw in files.items()
            ],
        },
    )
    root = tmp_path / "preferred-preparation"
    root.mkdir()
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    request = tmp_path / "request.json"
    request.write_text(json.dumps(data))
    return request, tmp_path / "survey.sqlite"


def evaluate(request, index, *, maximum=1_048_576):
    return evaluate_interface_survey(
        request,
        index,
        limits=SurveyEvaluationLimits(local_nodes=10, local_realizations=10, release_site_pairs=10),
        max_evaluations=1,
        max_checkpoint_bytes=maximum,
        should_stop=lambda: True,
    )


def test_interrupted_reference_import_can_restart_without_repair(tmp_path, monkeypatch):
    request, index = inputs(tmp_path)
    original = SurveyIndex.put_object
    calls = 0

    def interrupted(self, data):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected input interruption")
        return original(self, data)

    with monkeypatch.context() as patch:
        patch.setattr(SurveyIndex, "put_object", interrupted)
        with pytest.raises(OSError, match="injected"):
            evaluate(request, index)
    assert not index.exists()
    assert not list(tmp_path.glob(".hop-survey-input-*"))
    result = evaluate(request, index)
    assert result["evaluations"] == 0
    assert result["coverage"]["excluded_pairs"] == 0
    assert result["record_objects"] == 2


def test_storage_full_reference_import_can_restart_after_capacity_changes(tmp_path):
    request, index = inputs(tmp_path, large=True)
    with pytest.raises(sqlite3.OperationalError, match="full"):
        evaluate(request, index)
    assert not index.exists()
    result = evaluate(request, index, maximum=2_097_152)
    assert result["record_objects"] == 2
    assert result["coverage"]["unexamined_pairs"] == 65536


def test_reference_initialization_never_replaces_an_existing_target(tmp_path):
    request, index = inputs(tmp_path)
    index.write_bytes(b"existing owner")
    with pytest.raises(FileExistsError):
        evaluate(request, index)
    assert index.read_bytes() == b"existing owner"
