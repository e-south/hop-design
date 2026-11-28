"""
--------------------------------------------------------------------------------
HOP Design
tests/unit/test_edition_inventory.py

Characterize edition inventory names, ordinary files and filesystem failures.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import errno
import os
from pathlib import Path

import pytest

from hop_design.design.construction.editions.storage import inventory


@pytest.mark.parametrize("relative", [False, True])
def test_inventory_retains_nested_hidden_unicode_and_spaced_names(tmp_path, monkeypatch, relative):
    root = tmp_path / "edition dir"
    (root / "nested" / "empty").mkdir(parents=True)
    expected = {"ordinary.json", ".hidden", "nested/Δ space name.txt", "nested/deeper/value.txt"}
    for name in expected:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("recorded bytes")
    if relative:
        monkeypatch.chdir(tmp_path)
        root = Path(root.name)
    assert inventory(root) == expected


def test_empty_directories_do_not_become_artifacts(tmp_path):
    (tmp_path / "empty" / "nested").mkdir(parents=True)
    assert inventory(tmp_path) == set()


@pytest.mark.parametrize("kind", ["file", "directory", "broken"])
def test_inventory_rejects_file_directory_and_broken_symlinks(tmp_path, kind):
    root = tmp_path / "edition"
    root.mkdir()
    target = tmp_path / "target"
    if kind == "file":
        target.write_text("outside edition")
    elif kind == "directory":
        target.mkdir()
    try:
        (root / "link").symlink_to(target, target_is_directory=kind == "directory")
    except OSError as error:
        pytest.skip(f"Symlink creation is unavailable: {error}")
    with pytest.raises(ValueError, match="cannot be symlinks"):
        inventory(root)


def test_inventory_requires_an_ordinary_directory_root(tmp_path):
    missing = tmp_path / "missing"
    ordinary = tmp_path / "file"
    ordinary.write_text("not a directory")
    for root in (missing, ordinary):
        with pytest.raises(ValueError, match="ordinary directory"):
            inventory(root)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(tmp_path, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlink creation is unavailable: {error}")
    with pytest.raises(ValueError, match="ordinary directory"):
        inventory(alias)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Named pipes are unavailable")
def test_inventory_rejects_special_files_without_opening_them(tmp_path):
    os.mkfifo(tmp_path / "pipe")
    with pytest.raises(ValueError, match="must be ordinary files"):
        inventory(tmp_path)


@pytest.mark.skipif(os.name == "nt", reason="Backslash cannot be a Windows filename character")
@pytest.mark.parametrize("name", ["bad\\name.txt", "bad\\directory/member.txt"])
def test_inventory_rejects_unsafe_artifact_names(tmp_path, name):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("invalid artifact name")
    with pytest.raises(ValueError, match="normalized relative paths"):
        inventory(tmp_path)


@pytest.mark.parametrize("blocked_root", [False, True])
def test_inventory_preserves_scandir_permission_error_behavior(tmp_path, monkeypatch, blocked_root):
    root = tmp_path / "edition"
    blocked = root if blocked_root else root / "blocked"
    blocked.mkdir(parents=True)
    (blocked / "unreadable.json").write_text("unreadable bytes")
    if not blocked_root:
        (root / "readable.json").write_text("readable bytes")
    scan = os.scandir

    def denied(path):
        if Path(path) == blocked:
            raise PermissionError(errno.EACCES, "Access denied", os.fspath(path))
        return scan(path)

    monkeypatch.setattr(os, "scandir", denied)
    # Discovery historically skips unreadable directory listings. The public
    # edition reader still rejects any missing manifested file afterward.
    assert inventory(root) == (set() if blocked_root else {"readable.json"})
