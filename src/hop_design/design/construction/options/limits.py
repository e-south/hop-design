"""Bound the temporary inventory before allocation and atomic publication."""

from pathlib import Path

MAX_FILES = 19_900
MAX_BYTES = 500 * 1024 * 1024


def require_inventory_size(count: int, size: int) -> None:
    if count > MAX_FILES or size > MAX_BYTES:
        raise ValueError("Options exceed the packet bound; narrow the request or budget.")


def check_generated_inventory(root: Path) -> None:
    count = size = 0
    for path in root.rglob("*"):
        if path.is_file():
            count += 1
            size += path.stat().st_size
            require_inventory_size(count, size)
