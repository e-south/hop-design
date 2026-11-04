#!/usr/bin/env python3
"""
--------------------------------------------------------------------------------
HOP Design
scripts/check_public_safety.py

Rejects private identities and secret-like material on public repository surfaces.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import re
import stat
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = Path("scripts/check_public_safety.py")
MAX_FILE_BYTES = 2_000_000
PATTERNS = {
    "machine-local user path": re.compile(r"(?:/Users/|/home/[A-Za-z0-9._-]+/|Dropbox/projects)"),
    "neighbor-repository identity": re.compile(
        r"(?:research[\s_-]+studies|manufold|cruncher|dnadesign|eco1|retron)", re.IGNORECASE
    ),
    "private key material": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "token-like credential": re.compile(
        r"(?:sk-(?:proj-)?|gh[pousr]_|github_pat_|glpat-|xox[baprs]-)[A-Za-z0-9_-]{12,}"
    ),
    "cloud access key": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
}


def candidate_paths() -> list[Path]:
    """Inventory tracked and nonignored untracked files, including ignored tracked files."""
    root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=REPO_ROOT, stderr=subprocess.PIPE
    )
    if Path(root.decode().rstrip("\n")).resolve() != REPO_ROOT.resolve():
        raise ValueError("Public-safety scanning requires the repository root.")
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPO_ROOT,
        stderr=subprocess.PIPE,
    )
    return [
        REPO_ROOT / name
        for name in sorted(set(names.decode(errors="surrogateescape").split("\0")))
        if name and Path(name) != POLICY_PATH
    ]


def has_symlink(path: Path) -> bool:
    """Reject a linked entry or parent without reading the referenced content."""
    current = REPO_ROOT
    for part in path.relative_to(REPO_ROOT).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def oversized(label: str) -> str:
    return f"{label}: file exceeds the 2 MB public-safety limit"


def scan_content(content: bytes, label: str) -> tuple[int, list[str]]:
    """Apply the same byte and text policy to source and distribution members."""
    if len(content) > MAX_FILE_BYTES:
        return 0, [oversized(label)]
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return 0, []
    errors = []
    for category, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"{label}:{line}: {category}")
    return 1, errors


def scan_repository() -> tuple[int, list[str]]:
    errors: list[str] = []
    scanned = 0
    for path in candidate_paths():
        relative = path.relative_to(REPO_ROOT).as_posix()
        if has_symlink(path):
            errors.append(f"{relative}: repository symlink is not allowed")
            continue
        if not path.exists():
            continue
        if not path.is_file():
            errors.append(f"{relative}: repository entry is not a regular file")
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            errors.append(oversized(relative))
            continue
        count, violations = scan_content(path.read_bytes(), relative)
        scanned += count
        errors.extend(violations)
    return scanned, errors


def member_errors(
    name: str, size: int, *, regular: bool, directory: bool, seen: set[str]
) -> list[str]:
    """Validate an archive member before any body is opened or extracted."""
    normalized = name.removesuffix("/") if directory else name
    if (
        not normalized
        or "\\" in normalized
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
    ):
        return [f"{name}: unsafe member path"]
    if normalized in seen:
        return [f"{name}: duplicate member"]
    seen.add(normalized)
    if not regular and not directory:
        return [f"{name}: link or special member is not allowed"]
    if size > MAX_FILE_BYTES:
        return [oversized(name)]
    return []


def scan_distribution(path: Path) -> tuple[int, list[str]]:
    """Check the exact wheel or source archive without extracting any member."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"distribution must be a regular, unlinked file: {path.name}")
    scanned = 0
    errors: list[str] = []
    seen: set[str] = set()
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                mode = stat.S_IFMT(item.external_attr >> 16)
                directory = item.is_dir() and mode in {0, stat.S_IFDIR}
                violations = member_errors(
                    item.filename,
                    item.file_size,
                    regular=not item.is_dir() and mode in {0, stat.S_IFREG},
                    directory=directory,
                    seen=seen,
                )
                if not violations and not directory:
                    with archive.open(item) as source:
                        count, violations = scan_content(
                            source.read(MAX_FILE_BYTES + 1), item.filename
                        )
                    scanned += count
                errors.extend(violations)
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            for item in archive:
                violations = member_errors(
                    item.name,
                    item.size,
                    regular=item.isfile(),
                    directory=item.isdir(),
                    seen=seen,
                )
                if not violations and not item.isdir():
                    source = archive.extractfile(item)
                    if source is None:
                        raise ValueError("distribution member has no regular-file content")
                    with source:
                        count, violations = scan_content(source.read(MAX_FILE_BYTES + 1), item.name)
                    scanned += count
                errors.extend(violations)
    else:
        raise ValueError(f"unsupported distribution format: {path.name}")
    return scanned, [f"{path.name}!{error}" for error in errors]


def main(argv: Sequence[str] = ()) -> int:
    """Scan repository sources or explicitly named distributions; never print file bodies."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distribution", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    label = "Distribution-safety" if args.distribution else "Public-safety"
    try:
        if args.distribution:
            scanned = 0
            errors = []
            for path in args.distribution:
                count, violations = scan_distribution(path)
                scanned += count
                errors.extend(violations)
        else:
            scanned, errors = scan_repository()
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        tarfile.TarError,
        zipfile.BadZipFile,
        RuntimeError,
        NotImplementedError,
    ) as error:
        print(f"{label} scan failed: {error}")
        return 1
    if errors:
        print(f"{label} failures:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"{label} scan: ok ({scanned} text files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
