"""Evaluate a bounded set of explicitly permitted strict product requests."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.runtime import producer_identity
from hop_design.export.construction.scaffold.discovery_report import discovery_report
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.serialization import canonical_json_bytes

from ..execution.feedback import DiscoveryFeedback
from ..options.explore import _explore_with_receipts
from ..options.limits import check_generated_inventory, require_inventory_size
from ..packets.publication import SourceBoundConstructionPacket
from ..public import VerifiedConstructionBundle
from .prepare import prepare_scaffold_discovery
from .records import branch_record, discovery_summary
from .scheduling import evaluate_plan


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldDiscovery(SourceBoundConstructionPacket):
    """Complete preparations and scoped failures under an explicit product intention."""

    _packet_schema: ClassVar[str] = "hop.scaffold-discovery-packet/v1"


def discover_scaffolds(
    path: str | Path,
    *,
    previous: str | Path | None = None,
    first_choices: int | None = None,
) -> ScaffoldDiscovery:
    """Evaluate permitted preparation branches; preserve every hard requirement."""
    return _discover_with_receipts(path, previous=previous, first_choices=first_choices)[0]


def _discover_with_receipts(
    path: str | Path,
    *,
    previous: str | Path | None = None,
    first_choices: int | None = None,
    start_pair: int = 0,
    local_source: Path | None = None,
    feedback: DiscoveryFeedback | None = None,
) -> tuple[ScaffoldDiscovery, dict[str, VerifiedConstructionBundle]]:
    """Retain this invocation's verified complete constructions for its caller."""
    producer = producer_identity()
    prepared = prepare_scaffold_discovery(path)
    preview = json.loads(prepared.json_bytes)
    if preview["status"] != "ready":
        raise ValueError(prepared.report_text)
    progressive = (
        previous is not None or first_choices is not None or start_pair > 0 or feedback is not None
    )
    if progressive and (len(preview["branches"]) != 1 or preview.get("search_targets")):
        raise ValueError("Progressive scaffold execution requires one untargeted branch.")
    roots = prepared._roots
    if previous is not None:
        roots = (*roots, ProtectedRoot.capture(previous))
    admitted = {}
    with tempfile.TemporaryDirectory(prefix="hop-scaffold-discovery-") as temporary:
        root = Path(temporary)

        def evaluate(
            branch: dict[str, Any], ordinal: int
        ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
            request = root / f"branch-{ordinal:04d}.json"
            request.write_bytes(canonical_json_bytes(branch["request"]))
            explored, receipts = _explore_with_receipts(
                request,
                max_continuations=preview["bounds"]["max_continuations_per_branch"],
                previous=None if previous is None else Path(previous) / "branches/0000",
                start_pair=start_pair,
                local_source=local_source,
                first_choices=first_choices,
                feedback=feedback,
                objective=ScaffoldDiscoveryRequest.model_validate_json(
                    dict(prepared._files)["request.json"]
                ).objective,
            )
            explored.write(root / "branches" / f"{ordinal:04d}")
            record, complete = branch_record(
                root, branch, json.loads(explored.json_bytes), ordinal, receipts
            )
            admitted.update(
                {f"branch-{ordinal + 1:04d}-{label}": proof for label, proof in receipts.items()}
            )
            check_generated_inventory(root)
            return record, complete

        branches, options, schedule = evaluate_plan(preview, evaluate)
        if progressive:
            # The packet retains the standard, fully examined-prefix contract.
            # The execution owner separately records requested effort and policy.
            actual = branches[0]["coverage"]["max_continuations"]
            if actual != preview["bounds"]["max_continuations_per_branch"]:
                authored = json.loads(dict(prepared._files)["request.json"])
                authored["max_continuations_per_branch"] = actual
                effective = root / "effective-search.json"
                effective.write_bytes(canonical_json_bytes(authored))
                prepared = prepare_scaffold_discovery(effective)
                preview = json.loads(prepared.json_bytes)
                _, _, schedule = evaluate_plan(
                    preview, lambda branch, ordinal: (branches[0], options)
                )
        prepared.write(root / "intent")
        (root / "effective-search.json").unlink(missing_ok=True)
        summary = discovery_summary(preview, producer, branches, options, schedule)
        files = {
            p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }
    drawings, report = discovery_report(summary, files)
    files.update(drawings)
    require_inventory_size(len(files), sum(map(len, files.values())))
    if producer_identity() != producer:
        raise ValueError("HOP producer changed during scaffold discovery.")
    packet = ScaffoldDiscovery._create(files, summary, report)
    object.__setattr__(packet, "_roots", roots)
    return packet, admitted
