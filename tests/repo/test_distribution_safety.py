"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_distribution_safety.py

Checks actual distribution members before extraction or installation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import io
import stat
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

SCANNER = Path(__file__).resolve().parents[2] / "scripts/check_public_safety.py"


def archive(path: Path, name: str, content: bytes, *, link: bool = False) -> None:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path, "w") as output:
            entry = zipfile.ZipInfo(name)
            entry.create_system = 3
            if link:
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            output.writestr(entry, content)
    else:
        with tarfile.open(path, "w:gz") as output:
            entry = tarfile.TarInfo(name)
            if link:
                entry.type = tarfile.SYMTYPE
                entry.linkname = "outside"
                output.addfile(entry)
            else:
                entry.size = len(content)
                output.addfile(entry, io.BytesIO(content))


def scan(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCANNER), "--distribution", str(path)],
        cwd=path.parent,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("suffix", [".whl", ".tar.gz"])
def test_clean_distribution_is_scanned_without_a_git_checkout(tmp_path: Path, suffix: str):
    path = tmp_path / ("package" + suffix)
    archive(path, "package/module.py", b'"""Public molecular operations."""\n')
    result = scan(path)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Distribution-safety scan: ok (1 text files)" in result.stdout
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("suffix", [".whl", ".tar.gz"])
@pytest.mark.parametrize("fault", ["private", "credential", "oversized", "traversal", "link"])
def test_distribution_rejects_unsafe_members_without_extracting_or_disclosing(
    tmp_path: Path, suffix: str, fault: str
):
    path = tmp_path / ("package" + suffix)
    name = "package/module.py"
    content = b"ordinary content"
    expected = ""
    if fault == "private":
        content = ("path = '" + "/Users" + "/example/private'\n").encode()
        expected = "machine-local user path"
    elif fault == "credential":
        content = ("token = '" + "ghp" + "_" + "A" * 20 + "'\n").encode()
        expected = "token-like credential"
    elif fault == "oversized":
        content = b"x" * 2_000_001
        expected = "2 MB"
    elif fault == "traversal":
        name = "../escaped.py"
        expected = "unsafe member path"
    elif fault == "link":
        expected = "link"
    archive(path, name, content, link=fault == "link")

    result = scan(path)
    assert result.returncode == 1, result.stderr + result.stdout
    assert expected in result.stdout
    assert content.decode() not in result.stdout + result.stderr
    assert list(tmp_path.iterdir()) == [path]
    assert not (tmp_path.parent / "escaped.py").exists()


@pytest.mark.parametrize("suffix", [".whl", ".tar.gz"])
def test_distribution_does_not_exempt_a_member_named_like_the_policy(tmp_path: Path, suffix: str):
    path = tmp_path / ("package" + suffix)
    archive(path, "scripts/check_public_safety.py", ("/Users" + "/example/private").encode())
    result = scan(path)
    assert result.returncode == 1
    assert "machine-local user path" in result.stdout


@pytest.mark.parametrize("suffix", [".whl", ".tar.gz", ".zip"])
def test_unreadable_or_unsupported_archive_fails_closed(tmp_path: Path, suffix: str):
    path = tmp_path / ("package" + suffix)
    path.write_bytes(b"not an archive")
    result = scan(path)
    assert result.returncode == 1
    assert "distribution" in result.stdout.lower()


@pytest.mark.parametrize("suffix", [".whl", ".tar.gz"])
def test_duplicate_archive_members_are_rejected(tmp_path: Path, suffix: str):
    path = tmp_path / ("package" + suffix)
    name = "package/module.py"
    if suffix == ".whl":
        with zipfile.ZipFile(path, "w") as output:
            output.writestr(name, b"first")
            with pytest.warns(UserWarning, match="Duplicate name"):
                output.writestr(name, b"second")
    else:
        with tarfile.open(path, "w:gz") as output:
            for content in (b"first", b"second"):
                entry = tarfile.TarInfo(name)
                entry.size = len(content)
                output.addfile(entry, io.BytesIO(content))
    result = scan(path)
    assert result.returncode == 1
    assert "duplicate member" in result.stdout


@pytest.mark.parametrize("kind", [tarfile.LNKTYPE, tarfile.CHRTYPE])
def test_tar_link_or_device_is_rejected(tmp_path: Path, kind: bytes):
    path = tmp_path / "package.tar.gz"
    with tarfile.open(path, "w:gz") as output:
        entry = tarfile.TarInfo("package/special")
        entry.type = kind
        entry.linkname = "package/target"
        output.addfile(entry)
    result = scan(path)
    assert result.returncode == 1
    assert "link or special member" in result.stdout


def test_wheel_smoke_scans_exact_archives_before_extracting_or_installing():
    text = (SCANNER.parent / "wheel-smoke").read_text()
    command = 'scripts/check_public_safety.py --distribution "$wheel_path"'
    assert command in text
    assert '--distribution "$sdist_path"' in text
    assert text.index(command) < text.index('tar -xzf "$sdist_path"')
    assert text.index(command) < text.index("uv pip install")
