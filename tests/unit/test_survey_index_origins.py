"""Tracked checkpoints keep exact old bytes while identifying each new writer."""

import json
import sqlite3

import pytest

from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document

OLD = {"package_version": "1", "package_content": "old"}
NEW = {"package_version": "2", "package_content": "new"}


def test_a_tracked_writer_preserves_prefix_and_resolves_each_creator(tmp_path, monkeypatch):
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    path = tmp_path / "tracked.sqlite"
    monkeypatch.setattr(
        "hop_design.design.construction.surveys.storage.origins.authorize_transition",
        lambda source, target: "sha256:" + "a" * 64,
    )
    with SurveyIndex.create(path, request=request, producer=OLD, format_version=2) as saved:
        first = saved.put_object(b"first")
        saved.cache("original", b"old local")
        saved.append(0, step=0, record=b"old record", witness_count=1, exhausted=False)
        prefix = saved.logical_digest()
        saved.transition_producer(NEW)
        second = saved.put_object(b"second")
        assert saved.put_object(b"first") == first
        saved.append(0, step=1, record=b"new record", witness_count=0, exhausted=False)
        assert saved.object_creator(first) == OLD
        assert saved.object_creator(second) == NEW
        assert saved.cache_creator("original") == OLD
        assert saved.step_creator(0, step=0) == OLD
        assert saved.step_creator(0, step=1) == NEW
        assert saved.creator_producer == OLD
        assert saved.writer_producer == NEW
        assert saved.prefix_digest(0) == prefix
    with SurveyIndex.open(path, request=request, producer=NEW) as saved:
        assert saved.record(0, step=0) == b"old record"
        assert saved.record(0, step=1) == b"new record"
    with pytest.raises(ValueError, match="writer"):
        SurveyIndex.open(path, request=request, producer=OLD)
    # Reassigning a historical object to the latest creator removes it from
    # the sealed original prefix, even though every content hash still agrees.
    with sqlite3.connect(path) as db:
        db.execute("UPDATE objects SET creator=1 WHERE digest=?", (first,))
    with pytest.raises(ValueError, match="prefix"):
        SurveyIndex.open(path, request=request, producer=NEW)


def test_legacy_and_tracked_prefixes_have_the_same_logical_digest(tmp_path):
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    digests = []
    for format_version in (1, 2):
        with SurveyIndex.create(
            tmp_path / f"{format_version}.sqlite",
            request=request,
            producer=OLD,
            format_version=format_version,
        ) as saved:
            saved.cache("request", b"local")
            saved.put_object(b"unreferenced evidence")
            saved.append(0, step=0, record=b"a record", witness_count=0, exhausted=False)
            digests.append(saved.logical_digest())
    assert digests[0] == digests[1]


def test_exact_replay_keeps_captured_input_creators(tmp_path, monkeypatch):
    from hop_design.design.construction.surveys.replay import replay_evaluations
    from hop_design.design.runtime import producer_identity
    from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
    from hop_design.serialization import sha256_digest

    raw = b"captured input before any committed evaluation"
    digest = sha256_digest(raw)
    data = survey_document()
    data["source_context_objective"] = "paired_scaffold_completions"
    data["preferred_preparation"] = {
        "result_id": "hop:construction-space/" + "1" * 64 + "@1",
        "materialized_realization_id": "hop:materialized-construction/" + "2" * 64 + "@1",
        "files": [
            {
                "path": "construction-bundle.json",
                "digest": digest,
                "size_bytes": len(raw),
                "media_type": "application/json",
            }
        ],
    }
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    limits = SurveyEvaluationLimits(local_nodes=10, local_realizations=10, release_site_pairs=10)
    monkeypatch.setattr(
        "hop_design.design.construction.surveys.storage.origins.authorize_transition",
        lambda source, target: "sha256:" + "a" * 64,
    )
    with SurveyIndex.create(
        tmp_path / "source.sqlite", request=request, producer=OLD, format_version=2
    ) as saved:
        saved.put_object(raw)
        saved.transition_producer(NEW)
        with SurveyIndex.create(
            tmp_path / "replay.sqlite", request=request, producer=OLD, format_version=2
        ) as replay:
            replay.origins.import_history(saved.origins)
            replay_evaluations(saved, replay, limits, producer=producer_identity())
            assert replay.object_creator(digest) == OLD
