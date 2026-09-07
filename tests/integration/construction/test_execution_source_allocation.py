"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/construction/test_execution_source_allocation.py

Checks bounded source reads allocate for captured content rather than the safety ceiling.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import tracemalloc
from pathlib import Path

from hop_design.design.source_documents import _read_source_bytes


def test_small_document_does_not_allocate_its_large_safety_ceiling(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    content = b" " * 65536
    source.write_bytes(content)
    tracemalloc.start()
    try:
        actual = _read_source_bytes(source, max_bytes=64 * 1024 * 1024, source_label="test")
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert actual == content
    assert peak < 1024 * 1024
