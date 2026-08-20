from __future__ import annotations

import sys
from pathlib import Path

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
