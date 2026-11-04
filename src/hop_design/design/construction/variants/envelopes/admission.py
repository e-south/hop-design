"""Replay permission revisions and their added preparations before exposing a union."""

import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...discovery.admission import captured_discovery
from ...packets.capture import capture_packet, write_snapshot
from ..extended_pool import merge_captured_pools
from ..parameter_evaluation import selected_evaluation_request
from .evaluation import ScaffoldEnvelopeEvaluation, envelope_evaluation_summary
from .preview import load_scaffold_envelope_revision

if TYPE_CHECKING:
    from ..admission import CapturedVariants


@contextmanager
def captured_envelope_evaluation(path: str | Path, depth: int) -> Iterator["CapturedVariants"]:
    from ..admission import captured_variant_source
    from ..public import _admitted_exploration

    if depth > 8:
        raise ValueError("At most eight additional evaluation revisions can be nested.")
    protected, files = capture_packet(path, schema=ScaffoldEnvelopeEvaluation._packet_schema)
    with tempfile.TemporaryDirectory(prefix="hop-envelope-admission-") as temporary:
        root = Path(temporary)
        write_snapshot(files, root / "captured")
        with captured_variant_source(root / "captured/previous", depth=depth + 1) as previous:
            parent = _admitted_exploration(previous)
            preview = load_scaffold_envelope_revision(parent, root / "captured/preview")
            summary = json.loads(preview.json_bytes)
            if summary["status"] != "ready":
                raise ValueError("Evaluated envelope had a conflicting permission preview.")
            envelope = json.loads(dict(preview._files)["envelope-request.json"])
            request = json.loads(files["evaluation-request.json"])
            expected = selected_evaluation_request(
                envelope,
                summary["query"],
                request["max_branches"],
                request["max_continuations_per_branch"],
            )
            if (
                expected != request
                or canonical_json_bytes(request) != files["additional/intent/request.json"]
            ):
                raise ValueError("Evaluation disagrees with the explicit envelope revision.")
            with captured_discovery(root / "captured/additional") as additional:
                result = envelope_evaluation_summary(summary, request, additional[1])
                if canonical_json_bytes(result) != files["summary.json"]:
                    raise ValueError("Envelope evaluation summary disagrees with its records.")
                merged = merge_captured_pools(
                    root / "merged",
                    previous[0],
                    additional,
                    protected,
                    active_request=canonical_json_bytes(envelope),
                )
                yield merged, None, protected, sha256_digest(files["manifest.json"]), None
