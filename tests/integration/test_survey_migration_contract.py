"""The public maintenance operation refuses unsafe or incomplete publication."""

import json
import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.design.construction.surveys.storage import migration
from tests.support.interface_surveys import indexed_survey


def test_public_cli_migration_matches_api_and_reports_converted_work(tmp_path):
    path, source = indexed_survey(tmp_path)
    before = source.read_bytes()
    progress = []
    api = construction.migrate_interface_survey(
        path,
        source,
        destination=tmp_path / "api",
        on_converted=lambda count, size: progress.append((count, size)),
    )
    assert progress and progress[-1][0] == api["objects"] and progress[-1][1] > 0
    cli = CliRunner().invoke(
        app,
        [
            "construction",
            "survey",
            "migrate",
            str(path),
            "--index",
            str(source),
            "--out",
            str(tmp_path / "cli"),
        ],
    )
    assert cli.exit_code == 0, cli.output
    receipt = json.loads(cli.stdout)
    assert receipt["source_logical_digest"] == api["source_logical_digest"]
    assert source.read_bytes() == before
    assert "Converted" in cli.stderr
    inspected = construction.inspect_interface_survey(path, tmp_path / "cli/survey.sqlite")
    assert inspected["storage"]["format"] == 2
    assert inspected["storage"]["encoding"] == "zstd-blocks/v1"


def test_busy_source_and_existing_destination_are_refused(tmp_path):
    path, source = indexed_survey(tmp_path)
    before = source.read_bytes()
    with closing(sqlite3.connect(source)) as writer:
        writer.execute("BEGIN IMMEDIATE")
        with pytest.raises(ValueError, match=r"Stop.*writer"):
            construction.migrate_interface_survey(path, source, destination=tmp_path / "busy")
        writer.rollback()
    occupied = tmp_path / "exists"
    occupied.mkdir()
    (occupied / "keep").write_text("preserve")
    with pytest.raises(FileExistsError):
        construction.migrate_interface_survey(path, source, destination=occupied)
    assert (occupied / "keep").read_text() == "preserve" and source.read_bytes() == before


def test_capacity_cancel_and_publication_failure_leave_source_authoritative(tmp_path, monkeypatch):
    path, source = indexed_survey(tmp_path)
    before = source.read_bytes()
    with monkeypatch.context() as patch:
        patch.setattr(migration.shutil, "disk_usage", lambda path: SimpleNamespace(free=0))
        with pytest.raises(ValueError, match="free space"):
            construction.migrate_interface_survey(path, source, destination=tmp_path / "capacity")
    stopped = []
    with pytest.raises(InterruptedError, match="cancel"):
        construction.migrate_interface_survey(
            path,
            source,
            destination=tmp_path / "cancel",
            should_stop=lambda: bool(stopped),
            on_converted=lambda *args: stopped.append(args),
        )

    def fail(*args):
        raise OSError("publication failed")

    monkeypatch.setattr(migration, "publish_directory_create_only", fail)
    with pytest.raises(OSError, match="publication"):
        construction.migrate_interface_survey(path, source, destination=tmp_path / "failed")
    assert source.read_bytes() == before
    for name in ("busy", "capacity", "cancel", "failed"):
        assert not (tmp_path / name).exists() and not list(tmp_path.glob(f".{name}.*"))
