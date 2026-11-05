"""An explicit producer transition replays records without editing the source."""

import json

import pytest

from hop_design import construction
from hop_design.design.runtime import producer_identity
from tests.integration.test_survey_plane_pruning import execute, request_file
from tests.support.context_completion import LIMITS, records, request


def old_producer(monkeypatch):
    from hop_design.design.construction.surveys import execute as execution
    from hop_design.design.construction.surveys.navigation import history

    old = {**producer_identity(), "package_content": "sha256:" + "a" * 64}
    monkeypatch.setattr(execution, "producer_identity", lambda: old)
    monkeypatch.setattr(history, "producer_identity", lambda: old)
    return old


def test_upgrade_preserves_source_and_reissues_exclusions(tmp_path, monkeypatch):
    path = request_file(tmp_path)
    source = tmp_path / "old.sqlite"
    with monkeypatch.context() as context:
        old = old_producer(context)
        first = execute(path, source, 1)
    before = source.read_bytes()
    with pytest.raises(ValueError, match="producer"):
        execute(path, source, 1, resume=True)
    progress = []
    report = construction.upgrade_interface_survey(
        path,
        source,
        source_producer=old,
        destination=tmp_path / "upgraded",
        on_replayed=progress.append,
    )
    assert source.read_bytes() == before
    assert report["replayed_evaluations"] == 1
    assert report["source_producer"] == old
    assert report["producer"] == producer_identity()
    assert report["rebound_proof_references"] == 1
    assert report["coverage"] == first["coverage"]
    assert progress == [1]
    upgraded = tmp_path / "upgraded/survey.sqlite"
    assert construction.verify_interface_survey(path, upgraded)["replayed_evaluations"] == 1
    execute(path, upgraded, 1, resume=True)
    execute(path, tmp_path / "fresh.sqlite", 2)
    assert records(upgraded) == records(tmp_path / "fresh.sqlite")
    assert json.loads((tmp_path / "upgraded/transition.json").read_text()) == report


@pytest.mark.parametrize("field,value", [("next", None), ("witnesses", ["invented"])])
def test_drift_is_rejected_without_publishing_or_mutating_source(
    tmp_path, monkeypatch, field, value
):
    from hop_design.design.construction.surveys import replay

    path = request(tmp_path, "completion", completion=True)
    source = tmp_path / "source.sqlite"
    construction.evaluate_interface_survey(
        path, source, max_evaluations=1, continuation_batch_size=64, **LIMITS
    )
    before = source.read_bytes()
    original = replay.evaluate_step

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        result[field] = value
        return result

    monkeypatch.setattr(replay, "evaluate_step", changed)
    with pytest.raises(ValueError, match="replay"):
        construction.upgrade_interface_survey(
            path, source, source_producer=producer_identity(), destination=tmp_path / "upgraded"
        )
    assert source.read_bytes() == before
    assert not (tmp_path / "upgraded").exists()
    assert not list(tmp_path.glob(".upgraded.*"))


def test_upgrade_replays_batched_preparations_and_preserves_next_cursor(tmp_path):
    path = request(tmp_path, "completion", completion=True)
    source, fresh = tmp_path / "source.sqlite", tmp_path / "fresh.sqlite"
    construction.evaluate_interface_survey(
        path, source, max_evaluations=1, continuation_batch_size=64, **LIMITS
    )
    assert records(source)[0]["preceding_completion_steps"]
    construction.upgrade_interface_survey(
        path, source, source_producer=producer_identity(), destination=tmp_path / "upgraded"
    )
    upgraded = tmp_path / "upgraded/survey.sqlite"
    construction.evaluate_interface_survey(
        path, upgraded, max_evaluations=1, continuation_batch_size=64, resume=True, **LIMITS
    )
    construction.evaluate_interface_survey(
        path, fresh, max_evaluations=2, continuation_batch_size=64, **LIMITS
    )
    assert records(upgraded) == records(fresh)


def test_wrong_producer_and_existing_destination_are_not_overwritten(tmp_path):
    path = request_file(tmp_path)
    source = tmp_path / "source.sqlite"
    execute(path, source, 1)
    destination = tmp_path / "upgraded"
    wrong = {**producer_identity(), "package_content": "sha256:" + "0" * 64}
    with pytest.raises(ValueError, match="producer"):
        construction.upgrade_interface_survey(
            path, source, source_producer=wrong, destination=destination
        )
    assert not destination.exists()
    destination.mkdir()
    with pytest.raises(FileExistsError):
        construction.upgrade_interface_survey(
            path, source, source_producer=producer_identity(), destination=destination
        )


def test_resealed_proof_cannot_change_its_scientific_claim(tmp_path):
    from hop_design.design.construction.surveys.admission import open_survey
    from hop_design.design.construction.surveys.execute import load_request
    from hop_design.design.construction.surveys.index import SurveyIndex
    from hop_design.serialization import canonical_json_bytes

    path = request_file(tmp_path)
    source, corrupt = tmp_path / "source.sqlite", tmp_path / "corrupt.sqlite"
    execute(path, source, 1)
    producer = producer_identity()
    saved, limits = open_survey(source, request=load_request(path), producer=producer)
    with (
        saved,
        SurveyIndex.create(
            corrupt,
            request=load_request(path),
            producer=producer,
            limits=limits.model_dump(mode="json"),
        ) as changed,
    ):
        row = json.loads(saved.record(0, step=0))
        changed.put_object(saved.get_object(row["product_request"]))
        proof = json.loads(saved.get_object(row["empty_basal_planes"][0]))
        proof["facts"]["program_count"] += 1
        row["empty_basal_planes"] = [changed.put_object(canonical_json_bytes(proof))]
        changed.append(0, step=0, record=canonical_json_bytes(row), witness_count=0, exhausted=True)
    with pytest.raises(ValueError, match="exclusion proof"):
        construction.upgrade_interface_survey(
            path, corrupt, source_producer=producer, destination=tmp_path / "upgraded"
        )
    assert not (tmp_path / "upgraded").exists()


def test_cli_and_api_share_upgrade_receipt_and_records(tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app

    path = request_file(tmp_path)
    source = tmp_path / "source.sqlite"
    execute(path, source, 1)
    producer = tmp_path / "producer.json"
    producer.write_text(json.dumps(producer_identity()))
    expected = construction.upgrade_interface_survey(
        path, source, source_producer=producer_identity(), destination=tmp_path / "api"
    )
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "survey",
            "upgrade",
            str(path),
            "--index",
            str(source),
            "--source-producer",
            str(producer),
            "--out",
            str(tmp_path / "cli"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Replayed 1 evaluations" in result.stderr
    assert json.loads(result.stdout) == expected
    assert records(tmp_path / "cli/survey.sqlite") == records(tmp_path / "api/survey.sqlite")


def test_failed_or_interrupted_replay_never_leaves_an_admitted_destination(tmp_path):
    path = request_file(tmp_path)
    source = tmp_path / "source.sqlite"
    execute(path, source, 1)
    before = source.read_bytes()

    def stop(_count):
        raise KeyboardInterrupt("interrupted upgrade")

    with pytest.raises(KeyboardInterrupt):
        construction.upgrade_interface_survey(
            path,
            source,
            source_producer=producer_identity(),
            destination=tmp_path / "upgraded",
            on_replayed=stop,
        )
    assert source.read_bytes() == before
    assert not (tmp_path / "upgraded").exists()
    assert not list(tmp_path.glob(".upgraded.*"))
