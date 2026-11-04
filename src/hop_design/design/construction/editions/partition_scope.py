"""Admit a disjoint, complete division of one requested interface grid."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..intents.base import Source
from ..intents.execute import load_design_choices
from ..intents.resolve import resolve_design_request
from ..intents.results import InsertDesignChoices


@dataclass(frozen=True)
class PartitionSource:
    choices: InsertDesignChoices
    answer: dict[str, Any]


@dataclass(frozen=True)
class PartitionScope:
    resolution: dict[str, Any]
    request: InterfaceSurveyRequest
    sources: tuple[PartitionSource, ...]
    effort: dict[str, Any]


def admit_partitions(request: Source, directories: tuple[Path, ...]) -> PartitionScope:
    if not 2 <= len(directories) <= 256:
        raise ValueError("Combine between 2 and 256 disjoint discovery partitions.")
    if len({p.resolve() for p in directories}) != len(directories):
        raise ValueError("Discovery partitions must not repeat.")
    resolution = json.loads(resolve_design_request(request).json_bytes)
    if (
        resolution.get("schema") != "hop.resolved-design-request/v1"
        or resolution["intent"]["product"] != "released_insert"
    ):
        raise ValueError("Partition capture requires an exact-stem released-insert request.")
    parent = InterfaceSurveyRequest.model_validate_json(
        canonical_json_bytes(resolution["effective_request"])
    )
    expected = parent.model_dump(mode="json", by_alias=True, exclude={"targets"})
    permitted = {parent.targets.pair_at(i) for i in range(parent.targets.pair_count)}
    assigned: set[tuple[str, str]] = set()
    sources = []
    common_effort = None
    for directory in directories:
        choices = load_design_choices(directory)
        if not isinstance(choices, InsertDesignChoices):
            raise ValueError("Each partition must be an ordinary released-insert discovery.")
        local = choices._pool._request
        if local.model_dump(mode="json", by_alias=True, exclude={"targets"}) != expected:
            raise ValueError("Partition molecular permissions differ from the declared request.")
        pairs = {local.targets.pair_at(i) for i in range(local.targets.pair_count)}
        if not pairs <= permitted or pairs & assigned:
            raise ValueError("Partition target grids overlap or exceed the declared request.")
        assigned.update(pairs)
        effort = json.loads((directory / "effort.json").read_bytes())
        if common_effort is not None and effort != common_effort:
            raise ValueError("Partition execution policies differ.")
        common_effort = effort
        sources.append(PartitionSource(choices, choices.query()))
    if assigned != permitted:
        raise ValueError("Partitions do not cover the entire declared request grid.")
    assert common_effort is not None
    # The caller's argument order must not change the resulting edition identity.
    sources.sort(key=lambda s: s.answer["request_digest"])
    return PartitionScope(resolution, parent, tuple(sources), common_effort)


def combined_metadata(scope: PartitionScope) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    origins = [
        {key: source.answer[key] for key in ("request_digest", "snapshot_digest", "coverage")}
        for source in scope.sources
    ]
    coverage = {
        key: sum(source.answer["coverage"][key] for source in scope.sources)
        for key in (
            "target_pairs",
            "supported_pairs",
            "excluded_pairs",
            "unresolved_pairs",
            "unexamined_pairs",
        )
    }
    paths = [path for source in scope.sources for path in source.answer["paths"]]
    for side in ("left", "right"):
        coverage[f"supported_{side}_words"] = len({p["values"][f"{side}_end_word"] for p in paths})
        coverage[f"target_{side}_words"] = getattr(scope.request.targets, f"{side}_count")
    return {
        "schema": "hop.partitioned-discovery-capture/v1",
        "request_digest": sha256_digest(canonical_json_bytes(scope.request)),
        "sources": origins,
        "effort": scope.effort,
        "coverage": coverage,
        "search_performed": False,
        "molecular_replay": "captured_preparations_only",
        "allocation": "independent_per_partition",
    }, paths
