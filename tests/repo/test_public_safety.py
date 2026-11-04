"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_public_safety.py

Checks that public files reject private identifiers without disclosing their contents.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts import check_public_safety


@pytest.fixture(autouse=True)
def repository(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)


def test_ignored_runtime_output_does_not_become_repository_content(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    (tmp_path / ".gitignore").write_text(".artifacts/\n")
    runtime = tmp_path / ".artifacts"
    runtime.mkdir()
    (runtime / "log.txt").write_text("Workspace: " + "/Users" + "/example/private\n")
    (tmp_path / "README.md").write_text("Public source.\n")
    monkeypatch.setattr(check_public_safety, "REPO_ROOT", tmp_path)

    assert check_public_safety.main() == 0
    assert "Public-safety scan: ok (2 text files)" in capsys.readouterr().out


@pytest.mark.parametrize("directory", [".artifacts", ".venv"])
def test_tracked_files_remain_public_even_under_ignored_runtime_directories(
    tmp_path: Path, monkeypatch, capsys, directory: str
) -> None:
    (tmp_path / ".gitignore").write_text(f"{directory}/\n")
    target = tmp_path / directory / "published.txt"
    target.parent.mkdir()
    target.write_text("Workspace: " + "/Users" + "/example/private\n")
    subprocess.run(["git", "add", "-f", str(target)], cwd=tmp_path, check=True)
    monkeypatch.setattr(check_public_safety, "REPO_ROOT", tmp_path)

    assert check_public_safety.main() == 1
    assert f"{directory}/published.txt:1: machine-local user path" in capsys.readouterr().out


def test_another_file_named_like_the_scanner_is_not_exempt(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    target = tmp_path / "examples/check_public_safety.py"
    target.parent.mkdir()
    target.write_text("Workspace: " + "/Users" + "/example/private\n")
    monkeypatch.setattr(check_public_safety, "REPO_ROOT", tmp_path)

    assert check_public_safety.main() == 1
    assert "examples/check_public_safety.py:1: machine-local user path" in capsys.readouterr().out


def test_repository_scope_requires_the_selected_git_root(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    nested = tmp_path / "not-a-repository"
    nested.mkdir()
    monkeypatch.setattr(check_public_safety, "REPO_ROOT", nested)

    assert check_public_safety.main() == 1
    assert "requires the repository root" in capsys.readouterr().out


def test_tracked_path_cannot_follow_a_replaced_parent_directory(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    directory = tmp_path / "src"
    directory.mkdir()
    (directory / "module.py").write_text("ordinary content")
    subprocess.run(["git", "add", "src/module.py"], cwd=tmp_path, check=True)
    destination = tmp_path / "relocated"
    directory.rename(destination)
    directory.symlink_to(destination, target_is_directory=True)
    monkeypatch.setattr(check_public_safety, "REPO_ROOT", tmp_path)

    assert check_public_safety.main() == 1
    assert "symlink is not allowed" in capsys.readouterr().out


def test_public_safety_rejects_symlinks_and_oversized_files(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    target = tmp_path / "target.txt"
    target.write_text("ordinary content", encoding="utf-8")
    (tmp_path / "linked.txt").symlink_to(target)
    (tmp_path / "oversized.bin").write_bytes(b"x" * 2_000_001)
    monkeypatch.setattr(check_public_safety, "REPO_ROOT", tmp_path)

    assert check_public_safety.main() == 1
    output = capsys.readouterr().out
    assert "linked.txt: repository symlink is not allowed" in output
    assert "oversized.bin: file exceeds the 2 MB public-safety limit" in output


def test_public_safety_rejects_downstream_application_identity(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    (tmp_path / "application.txt").write_text(
        "This generic producer is affiliated with " + "ret" + "ron work.",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_public_safety, "REPO_ROOT", tmp_path)

    assert check_public_safety.main() == 1
    output = capsys.readouterr().out
    assert "application.txt:1: neighbor-repository identity" in output


@pytest.mark.parametrize(
    "identity",
    ["Research" + separator + "Studies" for separator in (" ", "\n", "_", "-")] + ["Manu" + "Fold"],
)
def test_public_safety_rejects_named_consumers_in_documentation(
    tmp_path: Path, monkeypatch, capsys, identity: str
) -> None:
    (tmp_path / "ownership.md").write_text(f"Client: {identity}\n", encoding="utf-8")
    monkeypatch.setattr(check_public_safety, "REPO_ROOT", tmp_path)

    assert check_public_safety.main() == 1
    output = capsys.readouterr().out
    assert "ownership.md:1: neighbor-repository identity" in output
    assert identity not in output


def test_public_safety_accepts_generic_product_and_consumer_responsibilities(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    (tmp_path / "ownership.md").write_text(
        "HOP owns molecular contracts and a public product roadmap.\n"
        "Client studies own experiments; manuscript systems own publication claims.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_public_safety, "REPO_ROOT", tmp_path)

    assert check_public_safety.main() == 0
    assert "Public-safety scan: ok (1 text files)" in capsys.readouterr().out
