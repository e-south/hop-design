"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/execution/producer.py

Binds resumable execution to package content and the Python dependency environment.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import platform
from importlib.metadata import version
from pathlib import Path

from hop_design.serialization import canonical_json_bytes, sha256_digest


def producer_identity() -> dict[str, str]:
    """Identify code bytes and runtime versions without machine-local path identity."""
    package = Path(__file__).resolve().parents[3]
    files = {
        path.relative_to(package).as_posix(): sha256_digest(path.read_bytes())
        for path in sorted(package.rglob("*.py"))
    }
    return {
        "package_version": version("hop-design"),
        "package_content": sha256_digest(canonical_json_bytes(files)),
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        **{name: version(name) for name in ("pydantic", "pydantic-core", "PyYAML", "typer")},
    }
