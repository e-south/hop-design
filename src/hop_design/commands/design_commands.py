"""Project admitted design actions into shell-quoted local handoff commands."""

import shlex
from pathlib import Path
from typing import Any


def design_commands(
    directory: Path,
    query: Path,
    answer: dict[str, Any],
    *,
    selection: dict[str, Any] | None = None,
    seed: int | None = None,
) -> str:
    """Executable local handoff; availability comes only from the shared answer."""
    prefix = ["hop-design", "design"]
    root = str(directory)
    filtering = ["--query", str(query)]
    lines = [
        "# Run in a fresh output directory outside the saved discovery.",
        shlex.join([*prefix, "query", root, *filtering]),
    ]
    if selection is not None and "select" in answer["actions"]:
        lines.extend(
            [
                shlex.join(
                    [
                        *prefix,
                        "select",
                        root,
                        *filtering,
                        "--preparation",
                        selection["materialized_realization_id"],
                        "--out",
                        "selection.json",
                    ]
                ),
                shlex.join(
                    [*prefix, "atlas", root, "--selection", "selection.json", "--out", "atlas"]
                ),
                shlex.join(
                    [
                        *prefix,
                        "retrieve",
                        root,
                        "--selection",
                        "selection.json",
                        "--out",
                        "preparation",
                    ]
                ),
            ]
        )
    if seed is not None and "select" in answer["actions"]:
        lines.extend(
            [
                "# Optional: reproduce the sampled choice separately.",
                shlex.join(
                    [
                        *prefix,
                        "sample",
                        root,
                        *filtering,
                        "--seed",
                        str(seed),
                        "--out",
                        "sampled-selection.json",
                    ]
                ),
            ]
        )
    if "continue_search" in answer["actions"]:
        lines.extend(
            [
                "# Optional: search further under the same permissions, then reload the view.",
                shlex.join([*prefix, "continue", root, "--evaluations", "64"]),
            ]
        )
    return "\n".join(lines)
