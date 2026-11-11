"""An explicit read-only source contract does not authorize foreign-producer execution."""

import json
import shutil
import sqlite3
from hashlib import sha256

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.design.construction.surveys.index import SurveyIndex
from tests.integration.test_edition_capture_admission import capture_pool as capture_pool


def source_contract(choices):
    from hop_design.design.runtime import producer_identity

    root = choices._directory
    paths = [root / "survey.sqlite", root / "effort.json", *sorted((root / "intent").rglob("*"))]
    return {
        "schema": "hop.recorded-design-source/v1",
        "producer": producer_identity(),
        "snapshot_digest": choices.query()["snapshot_digest"],
        "files": {
            path.relative_to(root).as_posix(): {
                "sha256": "sha256:" + sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
            for path in paths
            if path.is_file()
        },
    }


def test_explicit_capture_retains_original_producer_and_exact_handoff(
    capture_pool, tmp_path, monkeypatch
):
    from hop_design.design import runtime
    from hop_design.design.construction.surveys import choices as survey_choices
    from hop_design.design.construction.surveys import execute

    source = source_contract(capture_pool)
    selected = capture_pool.sample(seed=1)
    expected = tmp_path / "expected"
    capture_pool.retrieve(selected, expected)
    exporter = {**source["producer"], "package_content": "sha256:" + "a" * 64}
    monkeypatch.setattr(runtime, "producer_identity", lambda: exporter)
    monkeypatch.setattr(survey_choices, "producer_identity", lambda: exporter)
    monkeypatch.setattr(execute, "producer_identity", lambda: exporter)
    with pytest.raises(ValueError, match="producer"):
        construction.load_design_choices(capture_pool._directory)
    with pytest.raises(ValueError, match="producer"):
        construction.continue_design_discovery(capture_pool._directory, max_evaluations=1)
    edition = construction.freeze_design_choices(
        capture_pool._directory, tmp_path / "edition", compact=True, source_contract=source
    )
    assert edition.producer == source["producer"]
    origin = json.loads((edition._directory / "capture-origin.json").read_bytes())
    assert origin["source"] == source and origin["exporter"] == exporter
    assert origin["search_performed"] is False
    actual = tmp_path / "actual"
    edition.retrieve(edition.select(selected["materialized_realization_id"]), actual)
    assert {p.relative_to(actual): p.read_bytes() for p in actual.rglob("*") if p.is_file()} == {
        p.relative_to(expected): p.read_bytes() for p in expected.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("bad_field", ["checkpoint", "snapshot", "producer", "omitted_input"])
def test_mismatched_recorded_source_never_publishes(capture_pool, tmp_path, bad_field):
    source = source_contract(capture_pool)
    if bad_field == "checkpoint":
        source["files"]["survey.sqlite"]["sha256"] = "sha256:" + "0" * 64
    elif bad_field == "snapshot":
        source["snapshot_digest"] = "sha256:" + "0" * 64
    elif bad_field == "producer":
        source["producer"]["package_content"] = "sha256:" + "0" * 64
    else:
        del source["files"]["intent/summary.json"]
    with pytest.raises(ValueError):
        construction.freeze_design_choices(
            capture_pool._directory, tmp_path / "edition", compact=True, source_contract=source
        )
    assert not (tmp_path / "edition").exists()


def test_recorded_capture_cli_api_parity_and_refreeze(capture_pool, tmp_path):
    source = source_contract(capture_pool)
    source_file = tmp_path / "source.json"
    source_file.write_text(json.dumps(source))
    api = construction.freeze_design_choices(
        capture_pool._directory, tmp_path / "api", compact=True, source_contract=source
    )
    result = CliRunner().invoke(
        app,
        [
            "design",
            "freeze",
            str(capture_pool._directory),
            "--compact",
            "--source-contract",
            str(source_file),
            "--out",
            str(tmp_path / "cli"),
        ],
    )
    assert result.exit_code == 0, result.output
    cli = construction.load_atlas_edition(tmp_path / "cli")
    assert api.digest == cli.digest == json.loads(result.stdout)["edition_digest"]
    again = construction.freeze_design_choices(api._directory, tmp_path / "again", compact=True)
    assert again.producer == api.producer
    assert (again._directory / "capture-origin.json").read_bytes() == (
        api._directory / "capture-origin.json"
    ).read_bytes()
    assert {
        p.relative_to(api._directory): p.read_bytes() for p in api._directory.rglob("evidence.zip")
    } == {
        p.relative_to(again._directory): p.read_bytes()
        for p in again._directory.rglob("evidence.zip")
    }


def test_recorded_capture_admits_once_without_search(capture_pool, tmp_path, monkeypatch):
    from hop_design.design.construction import intents
    from hop_design.design.construction.surveys import execute

    admitted = []
    validate = SurveyIndex._validate

    def checked(index):
        admitted.append(index)
        return validate(index)

    def forbidden(*args, **kwargs):
        pytest.fail("Recorded capture must not search or resume")

    monkeypatch.setattr(SurveyIndex, "_validate", checked)
    monkeypatch.setattr(intents.execute, "discover_designs", forbidden)
    monkeypatch.setattr(intents.execute, "continue_design_discovery", forbidden)
    monkeypatch.setattr(execute, "evaluate_interface_survey", forbidden)
    construction.freeze_design_choices(
        capture_pool._directory,
        tmp_path / "edition",
        compact=True,
        source_contract=source_contract(capture_pool),
    )
    assert len(admitted) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        admitted[0]._db.execute("SELECT 1")


def test_exporter_identity_failure_does_not_leave_an_open_reader(
    capture_pool, tmp_path, monkeypatch
):
    from hop_design.design.construction.editions import recorded

    source = source_contract(capture_pool)
    readers = []
    open_survey = recorded.open_survey

    def opened(*args, **kwargs):
        index, limits = open_survey(*args, **kwargs)
        readers.append(index)
        return index, limits

    def fail_identity():
        raise ValueError("injected exporter identity failure")

    monkeypatch.setattr(recorded, "open_survey", opened)
    monkeypatch.setattr(recorded.runtime, "producer_identity", fail_identity)
    with pytest.raises(ValueError, match="injected exporter"):
        construction.freeze_design_choices(
            capture_pool._directory,
            tmp_path / "edition",
            compact=True,
            source_contract=source,
        )
    for index in readers:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            index._db.execute("SELECT 1")
    assert not (tmp_path / "edition").exists()


@pytest.mark.parametrize("damage", ["sidecar", "symlink", "rehashed_corruption"])
def test_recorded_capture_rejects_unsafe_or_corrupt_source(capture_pool, tmp_path, damage):
    root = tmp_path / "source"
    shutil.copytree(capture_pool._directory, root)
    source = source_contract(capture_pool)
    if damage == "sidecar":
        (root / "survey.sqlite-wal").touch()
    elif damage == "symlink":
        target = root / "effort.json"
        target.unlink()
        target.symlink_to(capture_pool._directory / "effort.json")
    else:
        with sqlite3.connect(root / "survey.sqlite") as db:
            block, raw = db.execute("SELECT id, content FROM blocks LIMIT 1").fetchone()
            db.execute(
                "UPDATE blocks SET content=? WHERE id=?",
                (raw[:-1] + bytes([raw[-1] ^ 1]), block),
            )
        path = root / "survey.sqlite"
        source["files"]["survey.sqlite"] = {
            "sha256": "sha256:" + sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
    with pytest.raises(ValueError):
        construction.freeze_design_choices(
            root,
            tmp_path / "edition",
            compact=True,
            source_contract=source,
        )
    assert not (tmp_path / "edition").exists()


@pytest.mark.parametrize("change", ["bytes", "replacement", "member_failure"])
def test_recorded_capture_rejects_mid_capture_changes_and_closes_reader(
    capture_pool, tmp_path, monkeypatch, change
):
    from hop_design.design.construction.editions import recorded

    root = tmp_path / "source"
    shutil.copytree(capture_pool._directory, root)
    source = source_contract(capture_pool)
    retrieve = recorded.retrieve_admitted_witness
    readers = []

    def changed(index, *args, **kwargs):
        if not readers:
            readers.append(index)
            if change == "member_failure":
                raise ValueError("injected member failure")
            path = root / "effort.json"
            if change == "replacement":
                replacement = tmp_path / "replacement.json"
                replacement.write_bytes(path.read_bytes())
                replacement.replace(path)
            else:
                path.write_bytes(path.read_bytes() + b"\n")
        return retrieve(index, *args, **kwargs)

    monkeypatch.setattr(recorded, "retrieve_admitted_witness", changed)
    with pytest.raises(ValueError):
        construction.freeze_design_choices(
            root,
            tmp_path / "edition",
            compact=True,
            source_contract=source,
        )
    assert not (tmp_path / "edition").exists()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        readers[0]._db.execute("SELECT 1")
