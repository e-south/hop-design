"""Evaluate an explicitly previewed envelope, preserving its earlier evidence."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...discovery.explore import discover_scaffolds
from ...options.limits import require_inventory_size
from ...packets.publication import SourceBoundConstructionPacket
from ..parameter_evaluation import selected_evaluation_request
from ..public import ScaffoldExploration, query_scaffold_variants
from ..source_capture import capture_exploration
from .preview import ScaffoldEnvelopePreview, preview_scaffold_envelope_revision


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldEnvelopeEvaluation(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.scaffold-envelope-evaluation-packet/v1"


def envelope_evaluation_summary(
    preview: dict[str, Any], request: dict[str, Any], additional: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": "hop.scaffold-envelope-evaluation/v1",
        "parent_result_digest": preview["parent_result_digest"],
        "query": preview["query"],
        "revision_digest": preview["revision_digest"],
        "envelope_digest": preview["envelope_digest"],
        "changes": preview["changes"],
        "evaluation_request_digest": sha256_digest(canonical_json_bytes(request)),
        "additional_request_digest": additional["request_digest"],
        "additional_complete_preparations": len(additional["options"]),
        "additional_coverage": additional["coverage"],
        "preserved": preview["preserved"],
    }


def evaluate_scaffold_envelope_revision(
    pool: ScaffoldExploration,
    preview: ScaffoldEnvelopePreview,
    *,
    max_branches: int,
    max_continuations_per_branch: int,
) -> ScaffoldEnvelopeEvaluation:
    saved = dict(preview._files)
    summary = json.loads(preview.json_bytes)
    choices = query_scaffold_variants(pool, summary["query"])
    expected = preview_scaffold_envelope_revision(pool, choices, json.loads(saved["revision.json"]))
    if expected._files != preview._files:
        raise ValueError("Stale or changed envelope preview; preview the current choices first.")
    if summary["status"] != "ready":
        raise ValueError("Envelope revision has conflicting requirements; inspect its preview.")
    envelope = json.loads(saved["envelope-request.json"])
    request = selected_evaluation_request(
        envelope, summary["query"], max_branches, max_continuations_per_branch
    )
    protected, parent_files = capture_exploration(pool)
    with tempfile.TemporaryDirectory(prefix="hop-envelope-evaluation-") as temporary:
        source = Path(temporary) / "request.json"
        source.write_bytes(canonical_json_bytes(request))
        additional = discover_scaffolds(source)
    files = {f"previous/{name}": data for name, data in parent_files.items()}
    files.update({f"additional/{name}": data for name, data in additional._files})
    files.update({f"preview/{name}": data for name, data in preview._files})
    files["evaluation-request.json"] = canonical_json_bytes(request)
    require_inventory_size(len(files), sum(map(len, files.values())))
    packet = ScaffoldEnvelopeEvaluation._create(
        files,
        envelope_evaluation_summary(summary, request, json.loads(additional.json_bytes)),
        "# Evaluated construction envelope revision\n\nOriginal evidence and query controls "
        "are retained. Only the explicitly previewed permissions changed. Complete "
        "preparations, scoped failures and incomplete coverage remain distinct.\n",
    )
    object.__setattr__(packet, "_roots", (protected, *preview._roots))
    return packet
