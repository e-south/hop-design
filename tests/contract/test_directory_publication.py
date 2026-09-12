"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_directory_publication.py

Tests atomic create-only directory publication.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import errno
import os
from contextlib import chdir
from pathlib import Path

import pytest

from hop_design.export import publication
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


@pytest.mark.parametrize("name", ["", ".", "..", "nested/child"])
@pytest.mark.parametrize("invalid_staging", [False, True])
def test_descriptor_publication_requires_immediate_child_names(
    name: str, invalid_staging: bool
) -> None:
    staging, destination = (
        (Path(name), Path("valid")) if invalid_staging else (Path("valid"), Path(name))
    )
    with pytest.raises(ValueError, match="immediate child names"):
        publication.publish_directory_create_only(staging, destination, parent_fd=-1)


def test_protected_publication_accepts_safe_parent_aliases(tmp_path: Path) -> None:
    parent, protected = tmp_path / "exports", tmp_path / "input"
    parent.mkdir()
    protected.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(parent, target_is_directory=True)
    publication.publish_directory_files_create_only(
        {"artifact.txt": b"complete\n"}, alias / "new-parent/published", protected_root=protected
    )
    assert (parent / "new-parent/published/artifact.txt").read_bytes() == b"complete\n"
    assert list(protected.iterdir()) == []


def test_protected_publication_retains_open_parent_through_path_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent, protected = tmp_path / "exports", tmp_path / "input"
    parent.mkdir()
    protected.mkdir()
    original_parent = tmp_path / "original-exports"
    original_open = publication._open_publication_parent

    def swap_after_open(destination: Path, protected_root: Path) -> int:
        descriptor = original_open(destination, protected_root)
        parent.rename(original_parent)
        parent.symlink_to(protected, target_is_directory=True)
        return descriptor

    monkeypatch.setattr(publication, "_open_publication_parent", swap_after_open)
    publication.publish_directory_files_create_only(
        {"artifact.txt": b"complete\n"}, parent / "published", protected_root=protected
    )
    assert (original_parent / "published/artifact.txt").read_bytes() == b"complete\n"
    assert list(protected.iterdir()) == []
    assert [path.name for path in original_parent.iterdir()] == ["published"]


def test_protected_publication_preserves_collision_and_cleans_staging(tmp_path: Path) -> None:
    parent, protected = tmp_path / "exports", tmp_path / "input"
    parent.mkdir()
    protected.mkdir()
    destination = parent / "published"
    destination.mkdir()
    (destination / "original.txt").write_bytes(b"original\n")
    with pytest.raises(FileExistsError):
        publication.publish_directory_files_create_only(
            {"artifact.txt": b"complete\n"}, destination, protected_root=protected
        )
    assert (destination / "original.txt").read_bytes() == b"original\n"
    assert [path.name for path in parent.iterdir()] == ["published"]
    assert list(protected.iterdir()) == []


@pytest.mark.parametrize("missing", ["new-parent", "new-parent/.."])
def test_protected_publication_checks_missing_parents_before_creating_them(
    tmp_path: Path, missing: str
) -> None:
    protected = tmp_path / "input"
    protected.mkdir()
    alias = tmp_path / "exports"
    alias.symlink_to(protected, target_is_directory=True)
    with pytest.raises(ValueError, match="outside the verified input bundle"):
        publication.publish_directory_files_create_only(
            {"artifact.txt": b"complete\n"},
            alias / missing / "published",
            protected_root=protected,
        )
    assert list(protected.iterdir()) == []


def test_protected_publication_normalizes_missing_parent_traversal(tmp_path: Path) -> None:
    protected, parent = tmp_path / "input", tmp_path / "exports"
    protected.mkdir()
    parent.mkdir()
    with pytest.raises(ValueError, match="outside the verified input bundle"):
        publication.publish_directory_files_create_only(
            {"artifact.txt": b"complete\n"},
            parent / "missing/../../input/published",
            protected_root=protected,
        )
    assert list(protected.iterdir()) == []
    assert list(parent.iterdir()) == []


def test_protected_publication_fails_before_writing_on_unsupported_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(publication.sys, "platform", "win32")
    with pytest.raises(OSError, match="requires directory descriptors") as error:
        publication.publish_directory_files_create_only(
            {"artifact.txt": b"complete\n"}, tmp_path / "published", protected_root=tmp_path
        )
    assert error.value.errno == errno.ENOTSUP
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("cleanup_operation", ["unlink", "rmdir"])
def test_protected_publication_cleanup_preserves_error_and_closes_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_operation: str
) -> None:
    protected = tmp_path / "input"
    protected.mkdir()
    descriptors = []
    original_open = os.open

    def track_open(*args, **kwargs):
        descriptor = original_open(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor

    def fail_publication(*args, **kwargs):
        raise FileExistsError("primary publication collision")

    def fail_cleanup(*args, **kwargs):
        raise OSError("racing cleanup entry")

    monkeypatch.setattr(publication.os, "open", track_open)
    monkeypatch.setattr(publication, "publish_directory_create_only", fail_publication)
    monkeypatch.setattr(publication.os, cleanup_operation, fail_cleanup)
    with pytest.raises(FileExistsError, match="primary publication collision"):
        publication.publish_directory_files_create_only(
            {"artifact.txt": b"complete\n"}, tmp_path / "published", protected_root=protected
        )
    for descriptor in descriptors:
        with pytest.raises(OSError) as error:
            os.fstat(descriptor)
        assert error.value.errno == errno.EBADF
    assert list(protected.iterdir()) == []
