#!/usr/bin/env python3
"""Select routine CI from a complete Git diff; unknown changes require full checks."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path

ARTWORK_PATHS = frozenset(
    {
        "README.md",
        "assets/README.md",
        "assets/hop-design-banner.svg",
        "assets/hop-design-banner.png",
        "assets/fonts/OFL-IBM-Plex-Sans.txt",
    }
)


def classify_paths(paths: Sequence[str]) -> str:
    return "artwork" if paths and set(paths) <= ARTWORK_PATHS else "full"


def changed_scope(event: str, base: str) -> str:
    if event not in {"pull_request", "push"} or not base or base == "0" * 40:
        return "full"
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("CI base must be a complete commit SHA")
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{base}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if exists.returncode:
        # An unavailable comparison cannot establish a restricted change scope.
        return "full"
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--no-renames",
            "--no-ext-diff",
            "--no-textconv",
            "-z",
            base,
            "HEAD",
            "--",
        ],
        capture_output=True,
        check=True,
    )
    paths = [os.fsdecode(name) for name in result.stdout.split(b"\0") if name]
    if any(Path(name).is_symlink() for name in paths):
        return "full"
    return classify_paths(paths)


def main() -> None:
    scope = changed_scope(os.environ.get("CI_EVENT", ""), os.environ.get("CI_BASE_SHA", ""))
    print(f"CI scope: {scope}")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"scope={scope}\n")


if __name__ == "__main__":
    main()
