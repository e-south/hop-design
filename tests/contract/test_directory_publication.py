"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_directory_publication.py

Tests atomic create-only directory publication.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from contextlib import chdir
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


def test_directory_publication_accepts_relative_destination(tmp_path: Path) -> None:
    staging = tmp_path / ".staging"
    staging.mkdir()
    (staging / "artifact.txt").write_text("complete\n", encoding="utf-8")

    with chdir(tmp_path):
        publish_directory_create_only(staging, Path("published"))

    assert not staging.exists()
    assert (tmp_path / "published/artifact.txt").read_text(encoding="utf-8") == "complete\n"


def test_relative_publication_does_not_follow_destination_link(tmp_path: Path) -> None:
    staging = tmp_path / ".staging"
    staging.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    destination = tmp_path / "published"
    destination.symlink_to(outside, target_is_directory=True)

    with chdir(tmp_path), pytest.raises(FileExistsError):
        publish_directory_create_only(staging, Path("published"))

    assert staging.is_dir()
    assert destination.is_symlink()
    assert list(outside.iterdir()) == []


def test_directory_publication_rejects_different_parents(tmp_path: Path) -> None:
    staging = tmp_path / ".staging"
    staging.mkdir()
    other = tmp_path / "other"
    other.mkdir()

    with pytest.raises(ValueError, match="sibling staging and destination"):
        publish_directory_create_only(staging, other / "published")

    assert staging.is_dir()
    assert not (other / "published").exists()
