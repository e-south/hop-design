"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/execution/storage.py

Publishes compressed canonical results in immutable, bounded batches.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import gzip
import io
import json
import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

from hop_design.design.source_documents import (
    _read_source_bytes,
    _unique_json_mapping,
    load_source_mapping,
)
from hop_design.export.publication import publish_directory_create_only
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .records import MAX_DOCUMENT_BYTES, BatchInventory


def read_mapping(path: Path) -> dict[str, object]:
    return load_source_mapping(
        path, max_bytes=MAX_DOCUMENT_BYTES, source_label="HOP local execution"
    )


def require_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"HOP local execution requires a non-symlink directory: {path}.")


def batch_paths(directory: Path) -> tuple[Path, ...]:
    require_directory(directory)
    paths = []
    for path in sorted(directory.iterdir()):
        require_directory(path)
        if path.name.startswith(".pending-"):
            continue
        if not path.name.isascii() or not path.name.isdecimal() or len(path.name) != 6:
            raise ValueError(f"Unexpected HOP local execution batch: {path.name}.")
        paths.append(path)
    return tuple(paths)


def read_inventory(path: Path, *, plan_digest: str, start: int) -> BatchInventory:
    if {entry.name for entry in path.iterdir()} != {"inventory.json", "results.jsonl.gz"}:
        raise ValueError("Local execution batch has an unexpected file inventory.")
    inventory = BatchInventory.model_validate_json(
        json.dumps(read_mapping(path / "inventory.json"))
    )
    if (
        inventory.plan_digest != plan_digest
        or inventory.start != start
        or path.name != f"{start:06d}"
    ):
        raise ValueError("Local execution batch plan or request order disagrees.")
    return inventory


def result_mappings(path: Path, inventory: BatchInventory) -> Iterator[dict[str, object]]:
    compressed = _read_source_bytes(
        path / "results.jsonl.gz",
        max_bytes=MAX_DOCUMENT_BYTES + 65536,
        source_label="HOP local execution batch",
    )
    if sha256_digest(compressed) != inventory.compressed_digest:
        raise ValueError("Local execution compressed result digest disagrees.")
    with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as stream:
        total = 0
        for expected in inventory.result_digests:
            content = stream.readline(MAX_DOCUMENT_BYTES + 1)
            total += len(content)
            if total > MAX_DOCUMENT_BYTES:
                raise ValueError("Local execution batch exceeds its decompressed byte limit.")
            if sha256_digest(content) != expected:
                raise ValueError("Local execution result digest disagrees.")
            mapping = json.loads(content, object_pairs_hook=_unique_json_mapping)
            if not isinstance(mapping, dict) or canonical_json_bytes(mapping) != content:
                raise ValueError("Local execution result must be canonical JSON.")
            yield mapping
        if stream.read(1):
            raise ValueError("Local execution batch contains extra result bytes.")


class BatchWriter:
    """Stream one batch to sibling staging; publish only its complete inventory."""

    def __init__(self, directory: Path, *, plan_digest: str, start: int) -> None:
        self.destination = directory / f"{start:06d}"
        self.staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=directory))
        self.plan_digest = plan_digest
        self.start = start
        self.digests: list[str] = []
        self.byte_count = 0
        self.file = (self.staging / "results.jsonl.gz").open("wb")
        self.stream = gzip.GzipFile(filename="", mode="wb", fileobj=self.file, mtime=0)

    def append(self, content: bytes) -> None:
        self.stream.write(content)
        self.digests.append(sha256_digest(content))
        self.byte_count += len(content)

    def publish(self) -> None:
        self.close()
        inventory = BatchInventory(
            plan_digest=self.plan_digest,
            start=self.start,
            result_digests=tuple(self.digests),
            compressed_digest=sha256_digest((self.staging / "results.jsonl.gz").read_bytes()),
        )
        with (self.staging / "inventory.json").open("wb") as handle:
            handle.write(canonical_json_bytes(inventory))
            handle.flush()
            os.fsync(handle.fileno())
        publish_directory_create_only(self.staging, self.destination)

    def close(self) -> None:
        self.stream.close()
        if not self.file.closed:
            self.file.flush()
            os.fsync(self.file.fileno())
            self.file.close()

    def discard(self) -> None:
        self.close()
        shutil.rmtree(self.staging, ignore_errors=True)
