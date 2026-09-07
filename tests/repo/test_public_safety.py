"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_public_safety.py

Checks that public files reject private identifiers without disclosing their contents.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts import check_public_safety


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
