"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_directory_publication.py

Tests atomic create-only directory publication.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hop_design.export.publication import publish_directory_create_only


def test_directory_publication_moves_a_complete_staging_directory(tmp_path: Path) -> None:
    staging = tmp_path / ".staging"
    staging.mkdir()
    (staging / "artifact.txt").write_text("complete\n", encoding="utf-8")
    destination = tmp_path / "published"

    publish_directory_create_only(staging, destination)

    assert not staging.exists()
    assert (destination / "artifact.txt").read_text(encoding="utf-8") == "complete\n"


def test_directory_publication_never_replaces_a_racing_destination(tmp_path: Path) -> None:
    staging = tmp_path / ".staging"
    staging.mkdir()
    (staging / "artifact.txt").write_text("complete\n", encoding="utf-8")
    destination = tmp_path / "published"
    destination.mkdir()

    with pytest.raises(FileExistsError):
        publish_directory_create_only(staging, destination)

    assert staging.is_dir()
    assert destination.is_dir()
    assert not (destination / "artifact.txt").exists()
