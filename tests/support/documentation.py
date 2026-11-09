"""
--------------------------------------------------------------------------------
HOP Design
tests/support/documentation.py

Reads a documentation entry and its focused child pages for contract checks.

Maintainer(s): HOP Design contributors
--------------------------------------------------------------------------------
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def read_documentation(relative_path: str) -> str:
    """Include the entry page and its same-stem topic directory, when present."""
    entry = REPO_ROOT / relative_path
    topics = entry.with_suffix("")
    pages = [entry, *sorted(topics.rglob("*.md"))] if topics.is_dir() else [entry]
    return "\n".join(page.read_text(encoding="utf-8") for page in pages)
