"""Bind copyable CLI calls to the exact immutable browser query."""

import json
from pathlib import Path
from typing import Any

from ..design_commands import design_commands
from .inspection_cache import state_key


def command_context(state: dict[str, Any], directory: Path, output: Path) -> dict[str, Any]:
    query = state["choices"]["query"]
    content = json.dumps(query, sort_keys=True, indent=2).encode()
    folder = output / "queries"
    folder.mkdir(exist_ok=True)
    path = folder / (state_key(query) + ".json")
    if path.is_symlink():
        raise ValueError("Command query cannot be a symbolic link.")
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("Published command query changed.")
    else:
        with path.open("xb") as handle:
            handle.write(content)
    return {
        "command_context": {"directory": str(directory), "query": str(path)},
        "commands": design_commands(
            directory, path, state["explanation"], selection=state["selection"]
        ),
    }
