"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/execution/local.py

Executes and resumes a finite ordered collection of independent local requests.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from hop_design.export.publication import publish_directory_create_only, publish_file_create_only
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..local_public import (
    LocalNeighborhoodDiscovery,
    _discover_request,
    _load_request,
    _verify_result_mapping,
)
from .producer import producer_identity
from .records import (
    MAX_BATCH_REQUESTS,
    MAX_DOCUMENT_BYTES,
    MAX_REQUESTS,
    CompletionRecord,
    ExecutionPlan,
)
from .storage import (
    BatchWriter,
    batch_paths,
    read_inventory,
    read_mapping,
    require_directory,
    result_mappings,
)


def _iter_results(
    directory: Path, plan: ExecutionPlan, *, stop_at: int | None = None
) -> Iterator[LocalNeighborhoodDiscovery]:
    require_directory(directory)
    if {entry.name for entry in directory.iterdir()} - {"plan.json", "batches", "complete.json"}:
        raise ValueError("Local execution contains unexpected files.")
    if canonical_json_bytes(read_mapping(directory / "plan.json")) != canonical_json_bytes(plan):
        raise ValueError("Local execution plan disagrees with the requested plan or producer.")
    plan_digest = sha256_digest(canonical_json_bytes(plan))
    completed = 0
    batch_digests = []
    for path in batch_paths(directory / "batches"):
        if stop_at is not None and completed == stop_at:
            break
        inventory = read_inventory(path, plan_digest=plan_digest, start=completed)
        batch_digests.append(sha256_digest(canonical_json_bytes(inventory)))
        for mapping in result_mappings(path, inventory):
            if completed >= len(plan.requests):
                raise ValueError("Local execution contains more results than requests.")
            receipt = _verify_result_mapping(mapping)
            result = receipt._verified_source()
            embedded = (
                result.neighborhood.request
                if isinstance(result, FoldbackNeighborhoodDiscoveryResult)
                else result.discovery.request
            )
            if canonical_json_bytes(embedded) != canonical_json_bytes(plan.requests[completed]):
                raise ValueError("Local execution result request disagrees with its plan position.")
            completed += 1
            yield receipt
    if stop_at is not None and completed != stop_at:
        raise ValueError("Local execution no longer contains the receipt's completed prefix.")
    marker = directory / "complete.json"
    if stop_at in (None, len(plan.requests)) and (marker.exists() or marker.is_symlink()):
        complete = CompletionRecord.model_validate_json(json.dumps(read_mapping(marker)))
        if completed != len(plan.requests) or complete != CompletionRecord(
            plan_digest=plan_digest, batch_digests=tuple(batch_digests)
        ):
            raise ValueError("Local execution completion record disagrees with its batches.")


@dataclass(frozen=True, init=False)
class LocalNeighborhoodBatch:
    """Execution receipt; finished requests may individually be truncated or infeasible."""

    _directory: Path
    _plan: ExecutionPlan
    completed_requests: int

    @property
    def planned_requests(self) -> int:
        return len(self._plan.requests)

    @property
    def finished(self) -> bool:
        return self.completed_requests == self.planned_requests

    def iter_results(self) -> Iterator[LocalNeighborhoodDiscovery]:
        """Replay saved results one at a time in declared request order."""
        yield from _iter_results(self._directory, self._plan, stop_at=self.completed_requests)


def discover_local_neighborhoods(
    source_paths: Sequence[str | Path],
    destination: str | Path,
    *,
    resume: bool = False,
    max_new_requests: int | None = None,
    batch_size: int = 8,
) -> LocalNeighborhoodBatch:
    """Checkpoint independent local queries without changing any query's search scope."""
    if not isinstance(resume, bool):
        raise ValueError("resume must be a Boolean.")
    if type(batch_size) is not int or not 1 <= batch_size <= MAX_BATCH_REQUESTS:
        raise ValueError(f"batch_size must be an integer from 1 to {MAX_BATCH_REQUESTS}.")
    if max_new_requests is not None and (type(max_new_requests) is not int or max_new_requests < 1):
        raise ValueError("max_new_requests must be a positive integer.")
    if isinstance(source_paths, str | Path) or not 1 <= len(source_paths) <= MAX_REQUESTS:
        raise ValueError(f"Provide an ordered collection of 1 to {MAX_REQUESTS} request paths.")
    requests = []
    request_bytes = 0
    for path in source_paths:
        request = _load_request(path)
        request_bytes += len(canonical_json_bytes(request))
        if request_bytes > MAX_DOCUMENT_BYTES:
            raise ValueError("Local execution plan exceeds its byte limit.")
        requests.append(request)
    plan = ExecutionPlan(producer=producer_identity(), requests=tuple(requests))
    plan_bytes = canonical_json_bytes(plan)
    if len(plan_bytes) > MAX_DOCUMENT_BYTES:
        raise ValueError("Local execution plan exceeds its byte limit.")
    plan_digest = sha256_digest(plan_bytes)
    output = Path(destination)
    if not resume:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace local execution: {output}.")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            (staging / "plan.json").write_bytes(plan_bytes)
            (staging / "batches").mkdir()
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    completed = sum(1 for _ in _iter_results(output, plan))
    stop = min(len(requests), completed + (max_new_requests or len(requests)))
    writer: BatchWriter | None = None
    try:
        for index in range(completed, stop):
            receipt = _discover_request(requests[index])
            content = receipt.json_bytes
            if writer is not None and writer.byte_count + len(content) > MAX_DOCUMENT_BYTES:
                if producer_identity() != plan.producer:
                    raise ValueError("Local execution producer changed during discovery.")
                writer.publish()
                writer = None
            if writer is None:
                writer = BatchWriter(output / "batches", plan_digest=plan_digest, start=index)
            writer.append(content)
            del receipt, content
            if len(writer.digests) == batch_size or index + 1 == stop:
                if producer_identity() != plan.producer:
                    raise ValueError("Local execution producer changed during discovery.")
                writer.publish()
                writer = None
        if stop == len(requests):
            digests = []
            count = 0
            for path in batch_paths(output / "batches"):
                inventory = read_inventory(path, plan_digest=plan_digest, start=count)
                count += len(inventory.result_digests)
                digests.append(sha256_digest(canonical_json_bytes(inventory)))
            marker = output / "complete.json"
            if not marker.exists():
                publish_file_create_only(
                    canonical_json_bytes(
                        CompletionRecord(plan_digest=plan_digest, batch_digests=tuple(digests))
                    ),
                    marker,
                )
    finally:
        if writer is not None:
            writer.discard()
    receipt_batch = object.__new__(LocalNeighborhoodBatch)
    object.__setattr__(receipt_batch, "_directory", output)
    object.__setattr__(receipt_batch, "_plan", plan)
    object.__setattr__(receipt_batch, "completed_requests", stop)
    return receipt_batch
