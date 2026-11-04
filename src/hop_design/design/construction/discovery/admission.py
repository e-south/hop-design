"""Rebind each saved branch to product intent before allowing molecular selection."""

import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from hop_design.export.publication import ProtectedRoot
from hop_design.serialization import canonical_json_bytes

from ..options.admission import admit_options
from ..packets.capture import capture_packet, write_snapshot
from ..public import VerifiedConstructionBundle
from ..verification import local_replay_scope
from .prepare import prepare_scaffold_discovery
from .records import branch_record, discovery_summary
from .scheduling import evaluate_plan

type CapturedDiscovery = tuple[
    Path, dict[str, Any], dict[str, VerifiedConstructionBundle], ProtectedRoot
]


@contextmanager
def captured_discovery(
    path: str | Path,
) -> Iterator[CapturedDiscovery]:
    protected, files = capture_packet(path, schema="hop.scaffold-discovery-packet/v1")
    with (
        local_replay_scope(),
        tempfile.TemporaryDirectory(prefix="hop-scaffold-admission-") as temporary,
    ):
        root = Path(temporary)
        write_snapshot(files, root)
        try:
            prepared = prepare_scaffold_discovery(root / "intent/request.json")
            preview = json.loads(prepared.json_bytes)
            if preview["status"] != "ready":
                raise ValueError("Saved discovery has conflicting requirements.")
            if prepared.json_bytes != files["intent/summary.json"]:
                raise ValueError("Saved discovery preview disagrees with the authored request.")
            receipts = {}
            expected_producer = None

            def evaluate(
                branch: dict[str, Any], ordinal: int
            ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
                nonlocal expected_producer
                folder = root / "branches" / f"{ordinal:04d}"
                if json.loads((folder / "inputs/request.json").read_bytes()) != branch["request"]:
                    raise ValueError("Saved preparation branch disagrees with permitted changes.")
                result, admitted = admit_options(folder)
                if result.get("search_objective") != preview.get("search_objective"):
                    raise ValueError("Branch search objective disagrees with discovery request.")
                if (
                    result["coverage"]["max_continuations"]
                    != preview["bounds"]["max_continuations_per_branch"]
                ):
                    raise ValueError("Branch continuation budget disagrees with discovery request.")
                if expected_producer is not None and expected_producer != result["producer"]:
                    raise ValueError("Discovery branches must share the producing implementation.")
                expected_producer = result["producer"]
                record, complete = branch_record(root, branch, result, ordinal, admitted)
                receipts.update(
                    {
                        f"branch-{ordinal + 1:04d}-{label}": receipt
                        for label, receipt in admitted.items()
                    }
                )
                return record, complete

            branches, options, schedule = evaluate_plan(preview, evaluate)
            if expected_producer is None:
                raise ValueError("A saved discovery must contain at least one evaluated branch.")
            summary = discovery_summary(preview, expected_producer, branches, options, schedule)
            if canonical_json_bytes(summary) != files["summary.json"]:
                raise ValueError("Discovery summary disagrees with verified branch outcomes.")
        except (KeyError, TypeError, IndexError, AttributeError) as error:
            raise ValueError("Malformed saved scaffold discovery.") from error
        yield root, summary, receipts, protected
