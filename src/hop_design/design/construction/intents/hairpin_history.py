"""Immutable discovery snapshots; prior explicit selections keep their authority."""

import json
from pathlib import Path
from typing import Any

from hop_design.models.construction.intents.execution import HairpinExecution
from hop_design.serialization import sha256_digest

from ..packets.capture import capture_packet
from ..packets.publication import SourceBoundConstructionPacket


class HairpinSnapshot(SourceBoundConstructionPacket):
    _packet_schema = "hop.hairpin-design-snapshot/v1"


def snapshot_paths(root: Path) -> list[Path]:
    """Only atomically published snapshots participate; staging folders stay private."""
    snapshots = root / "hairpin-snapshots"
    if not snapshots.exists():
        return []
    entries = sorted(p for p in snapshots.iterdir() if not p.name.startswith("."))
    if any(p.is_symlink() or not p.is_dir() or p.name != f"{i:04d}" for i, p in enumerate(entries)):
        raise ValueError("Hairpin snapshots must form an intact ordered history.")
    return entries


def snapshot_source(root: Path, digest: str | None = None) -> tuple[Path, HairpinExecution | None]:
    """Resolve an exact historical snapshot without silently rebinding a selection."""
    paths = snapshot_paths(root)
    if not paths:
        if (
            digest is not None
            and sha256_digest((root / "scaffolds/manifest.json").read_bytes()) != digest
        ):
            raise ValueError("Selected snapshot does not belong to this discovery.")
        return root / "scaffolds", None
    previous = None
    previous_count = 0
    if (root / "scaffolds").exists():
        previous = sha256_digest((root / "scaffolds/manifest.json").read_bytes())
        previous_count = json.loads((root / "scaffolds/summary.json").read_bytes())["coverage"][
            "evaluated_pairs"
        ]
    found = None
    for path in paths:
        _, files = capture_packet(path, schema=HairpinSnapshot._packet_schema)
        execution = HairpinExecution.model_validate_json(files["execution.json"])
        if execution.previous_snapshot_digest != previous:
            raise ValueError("Hairpin snapshot history has changed.")
        if execution.previous_evaluated_pairs != previous_count:
            raise ValueError("Hairpin snapshot progress disagrees with its preceding snapshot.")
        if json.loads(files["summary.json"]) != execution.model_dump(mode="json", by_alias=True):
            raise ValueError("Hairpin execution summary disagrees with its policy record.")
        if execution.snapshot_digest != sha256_digest(files["scaffolds/manifest.json"]):
            raise ValueError("Hairpin execution and molecular snapshot disagree.")
        page_count = json.loads(files["scaffolds/summary.json"])["coverage"]["evaluated_pairs"]
        expected_count = page_count + (previous_count if execution.schema_id.endswith("/v2") else 0)
        if execution.evaluated_pairs != expected_count:
            raise ValueError("Hairpin execution and examined coverage disagree.")
        previous = execution.snapshot_digest
        previous_count = execution.evaluated_pairs
        if digest is None or previous == digest:
            found = (path / "scaffolds", execution)
    if found is not None:
        return found
    legacy = root / "scaffolds"
    if legacy.exists() and sha256_digest((legacy / "manifest.json").read_bytes()) == digest:
        return legacy, None
    raise ValueError("Selected snapshot does not belong to this discovery.")


def validate_execution(execution: HairpinExecution, options: dict[str, Any]) -> None:
    """Check the declared stop against verified work; cancellation is not an exclusion."""
    coverage = options["coverage"]
    previous = execution.previous_evaluated_pairs
    paged = execution.schema_id.endswith("/v2")
    evaluated = coverage["evaluated_pairs"] + (previous if paged else 0)
    limit = min(coverage["recorded_pairs"], previous + execution.max_evaluations)
    if not paged:
        limit = min(64, limit)
    elif options.get("pair_window") != {"start": previous, "stop": evaluated}:
        raise ValueError("Hairpin page is not the next contiguous candidate window.")
    counts = [
        sum(
            option["selection"]["bundle_path"]
            == str(Path(candidate["outcome"]).parent / "construction")
            for option in options["options"]
        )
        for candidate in options["candidates"][0 if paged else previous :]
    ]
    reason = "evaluation_limit"
    if evaluated == coverage["recorded_pairs"]:
        reason = "recorded_pairs_examined"
    elif evaluated < limit:
        reason = "first_choices"
    first = execution.first_choices
    if execution.stopping_reason == "cancelled":
        if not (
            evaluated == execution.evaluated_pairs
            and previous < evaluated < limit
            and (first is None or sum(counts) < first)
        ):
            raise ValueError(
                "Hairpin stopping policy disagrees with its verified examined outcomes."
            )
        return
    valid = (
        evaluated == execution.evaluated_pairs
        and previous <= evaluated <= limit
        and execution.stopping_reason == reason
        and (evaluated == limit or (first is not None and sum(counts) >= first))
        and (first is None or sum(counts[:-1]) < first)
    )
    if not valid:
        raise ValueError("Hairpin stopping policy disagrees with its verified examined outcomes.")
