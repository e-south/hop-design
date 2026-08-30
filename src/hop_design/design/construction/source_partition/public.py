"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/source_partition/public.py

Loads source-partition files and exposes opaque portable discovery receipts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.publication import publish_directory_create_only
from hop_design.models.construction.source_partition import (
    SourcePartitionDiscoveryRequest,
    SourcePartitionDiscoveryResult,
)
from hop_design.serialization import canonical_json_bytes

from .discovery import discover_source_partitions


def _result_csv(result: SourcePartitionDiscoveryResult) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        (
            "candidate_id",
            "enzyme_ids",
            "disposition",
            "failure_codes",
            "realization_id",
            "retained_fragment_ids",
        )
    )
    realization_by_id = {item.realization_id: item for item in result.realizations}
    for disposition in result.dispositions:
        realization = (
            None
            if disposition.realization_id is None
            else realization_by_id[disposition.realization_id]
        )
        writer.writerow(
            (
                disposition.candidate_id,
                ";".join(disposition.enzyme_ids),
                disposition.disposition.value,
                ";".join(item.value for item in disposition.failure_codes),
                disposition.realization_id or "",
                (
                    ""
                    if realization is None
                    else ";".join(realization.selected.retained_fragment_ids)
                ),
            )
        )
    return output.getvalue().encode("utf-8")


@dataclass(frozen=True, init=False, repr=False)
class SourcePartitionDiscovery:
    """Opaque, portable receipt for one replay-verified source-partition search."""

    _result: SourcePartitionDiscoveryResult
    _json_bytes: bytes
    _csv_bytes: bytes

    @classmethod
    def _create(cls, result: SourcePartitionDiscoveryResult) -> Self:
        verified = SourcePartitionDiscoveryResult.model_validate(
            result.model_dump(mode="python", by_alias=True)
        )
        instance = object.__new__(cls)
        object.__setattr__(instance, "_result", verified)
        object.__setattr__(instance, "_json_bytes", canonical_json_bytes(verified))
        object.__setattr__(instance, "_csv_bytes", _result_csv(verified))
        return instance

    @property
    def problem_id(self) -> str:
        return self._result.problem_id

    @property
    def request_id(self) -> str:
        return self._result.request_id

    @property
    def result_id(self) -> str:
        return self._result.result_id

    @property
    def status(self) -> str:
        return self._result.status.value

    @property
    def candidate_space_size(self) -> int:
        return self._result.candidate_space_size

    @property
    def examined_nodes(self) -> int:
        return self._result.examined_nodes

    @property
    def accepted_realizations(self) -> int:
        return len(self._result.realizations)

    @property
    def realization_ids(self) -> tuple[str, ...]:
        return tuple(item.realization_id for item in self._result.realizations)

    @property
    def json_bytes(self) -> bytes:
        return self._json_bytes

    @property
    def csv_bytes(self) -> bytes:
        return self._csv_bytes

    def write(self, destination: str | Path) -> Path:
        """Atomically write canonical result and tidy candidate data into a new directory."""
        output = Path(destination)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing source-partition path: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            (staging / "result.json").write_bytes(self._json_bytes)
            (staging / "data.csv").write_bytes(self._csv_bytes)
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return output

    def __repr__(self) -> str:
        return f"SourcePartitionDiscovery(status={self.status!r}, result_id={self.result_id!r})"


def _load_request(path: str | Path) -> SourcePartitionDiscoveryRequest:
    mapping = load_source_mapping(path, source_label="HOP source-partition")
    if mapping.get("schema") != "hop.source-partition-request/v1":
        raise ValueError(f"Unsupported HOP source-partition schema: {mapping.get('schema')!r}.")
    return SourcePartitionDiscoveryRequest.model_validate_json(
        json.dumps(mapping, separators=(",", ":"))
    )


def discover_source_partition(source_path: str | Path) -> SourcePartitionDiscovery:
    """Load one strict request and discover bounded source partitions."""
    return SourcePartitionDiscovery._create(discover_source_partitions(_load_request(source_path)))


def load_verified_source_partition(result_path: str | Path) -> SourcePartitionDiscovery:
    """Load one source-partition result after exact molecular and search replay."""
    mapping = load_source_mapping(result_path, source_label="HOP source-partition result")
    if mapping.get("schema") != "hop.source-partition-result/v1":
        raise ValueError(
            f"Unsupported HOP source-partition result schema: {mapping.get('schema')!r}."
        )
    result = SourcePartitionDiscoveryResult.model_validate_json(
        json.dumps(mapping, separators=(",", ":"))
    )
    return SourcePartitionDiscovery._create(result)


__all__ = [
    "SourcePartitionDiscovery",
    "discover_source_partition",
    "load_verified_source_partition",
]
