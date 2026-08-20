#!/usr/bin/env python3
"""Fail when public repository surfaces contain private or secret-like material."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    ".hypothesis",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
}
SKIP_FILES = {"check_public_safety.py"}
PATTERNS = {
    "machine-local user path": re.compile(r"(?:/Users/|/home/[A-Za-z0-9._-]+/|Dropbox/projects)"),
    "neighbor-repository identity": re.compile(
        r"(?:research-studies|cruncher|dnadesign|eco1)", re.IGNORECASE
    ),
    "private key material": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "token-like credential": re.compile(
        r"(?:sk-(?:proj-)?|gh[pousr]_|github_pat_|glpat-|xox[baprs]-)[A-Za-z0-9_-]{12,}"
    ),
    "cloud access key": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
}


def candidate_paths() -> list[Path]:
    """Return repository paths that can enter history or artifacts."""
    return sorted(
        path
        for path in REPO_ROOT.rglob("*")
        if path.name not in SKIP_FILES and not SKIP_PARTS & set(path.parts)
    )


def main() -> int:
    """Scan repository text and report all public-safety violations."""
    errors: list[str] = []
    scanned = 0
    for path in candidate_paths():
        relative = path.relative_to(REPO_ROOT)
        if path.is_symlink():
            errors.append(f"{relative}: repository symlink is not allowed")
            continue
        if not path.is_file():
            continue
        if path.stat().st_size > 2_000_000:
            errors.append(f"{relative}: file exceeds the 2 MB public-safety limit")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{relative}:{line}: {label}")

    if errors:
        print("Public-safety failures:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Public-safety scan: ok ({scanned} text files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
