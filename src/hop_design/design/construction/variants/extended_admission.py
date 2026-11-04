"""Revalidate parent intent and complete added preparations before merging a saved pool."""

import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..discovery.admission import captured_discovery
from ..packets.capture import capture_packet, write_snapshot
from .extended_pool import merge_captured_pools
from .parameter_evaluation import (
    ScaffoldParameterEvaluation,
    evaluation_request,
    evaluation_summary,
)

if TYPE_CHECKING:
    from .admission import CapturedVariants


@contextmanager
def captured_parameter_evaluation(path: str | Path, depth: int) -> Iterator["CapturedVariants"]:
    from .admission import captured_variant_source
    from .public import _admitted_exploration, query_scaffold_variants

    if depth > 8:
        raise ValueError("At most eight additional evaluation revisions can be nested.")
    protected, files = capture_packet(path, schema=ScaffoldParameterEvaluation._packet_schema)
    with tempfile.TemporaryDirectory(prefix="hop-extended-admission-") as temporary:
        root = Path(temporary)
        write_snapshot(files, root / "captured")
        saved = json.loads(files["summary.json"])
        with captured_variant_source(root / "captured/previous", depth=depth + 1) as previous:
            parent = _admitted_exploration(previous)
            choices = query_scaffold_variants(parent, saved["query"])
            request = json.loads(files["evaluation-request.json"])
            expected = evaluation_request(
                parent, choices, request["max_branches"], request["max_continuations_per_branch"]
            )
            if (
                expected != request
                or canonical_json_bytes(request) != files["additional/intent/request.json"]
            ):
                raise ValueError(
                    "Additional evaluation changed inherited permissions or selected constraints."
                )
            with captured_discovery(root / "captured/additional") as additional:
                expected_summary = evaluation_summary(
                    parent.result_digest, saved["query"], request, additional[1]
                )
                if canonical_json_bytes(expected_summary) != files["summary.json"]:
                    raise ValueError(
                        "Additional evaluation summary disagrees with its verified records."
                    )
                merged = merge_captured_pools(root / "merged", previous[0], additional, protected)
                yield merged, None, protected, sha256_digest(files["manifest.json"]), None
