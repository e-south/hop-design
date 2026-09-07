"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/local_public.py

Loads standalone local-neighborhood requests and exposes opaque verified receipts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from hop_design.design.source_documents import SourceDocumentLimitError, load_source_mapping
from hop_design.export.publication import publish_directory_create_only
from hop_design.models.construction import LocalNeighborhoodFamily, LocalNeighborhoodRequest
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.serialization import canonical_json_bytes

from .basal import discover_basal_neighborhood
from .foldback import discover_foldback_neighborhood
from .verification import (
    VerifiedBasalNeighborhoodResult,
    VerifiedFoldbackNeighborhoodResult,
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)

_VerifiedLocalResult = VerifiedFoldbackNeighborhoodResult | VerifiedBasalNeighborhoodResult
_LocalResult = FoldbackNeighborhoodDiscoveryResult | BasalNeighborhoodDiscoveryResult
_LOCAL_EXECUTION_MAX = 100_000
_LOCAL_RESULT_MAX_BYTES = 64 * 1024 * 1024


def _canonical_local_result_bytes(
    result: _LocalResult,
    *,
    max_bytes: int = _LOCAL_RESULT_MAX_BYTES,
) -> bytes:
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1.")
    content = canonical_json_bytes(result)
    if len(content) > max_bytes:
        raise SourceDocumentLimitError(actual=len(content), max_bytes=max_bytes)
    return content


def _validate_local_execution_limits(*, max_search_nodes: int, max_realizations: int) -> None:
    for field, value in (
        ("max_search_nodes", max_search_nodes),
        ("max_realizations", max_realizations),
    ):
        if value > _LOCAL_EXECUTION_MAX:
            raise ValueError(f"{field} must not exceed {_LOCAL_EXECUTION_MAX}.")


def _validate_result_mapping_execution_limits(
    mapping: dict[str, object],
    *,
    result_container: str,
) -> None:
    container = mapping.get(result_container)
    if not isinstance(container, dict):
        return
    request = container.get("request")
    if not isinstance(request, dict):
        return
    search = request.get("search")
    if not isinstance(search, dict):
        return
    limits = {
        field: value
        for field in ("max_search_nodes", "max_realizations")
        if isinstance((value := search.get(field)), int) and not isinstance(value, bool)
    }
    if len(limits) == 2:
        _validate_local_execution_limits(
            max_search_nodes=limits["max_search_nodes"],
            max_realizations=limits["max_realizations"],
        )


def _family_result(
    verified: _VerifiedLocalResult,
) -> tuple[LocalNeighborhoodFamily, _LocalResult]:
    if isinstance(verified, VerifiedFoldbackNeighborhoodResult):
        return LocalNeighborhoodFamily.FOLDBACK, verified.result
    if isinstance(verified, VerifiedBasalNeighborhoodResult):
        return LocalNeighborhoodFamily.BASAL, verified.result
    raise TypeError("Local-neighborhood receipt requires a replay-verified local result.")


@dataclass(frozen=True, init=False, repr=False)
class LocalNeighborhoodDiscovery:
    """Opaque, portable receipt for one replay-verified local-neighborhood search."""

    _verified: _VerifiedLocalResult
    _json_bytes: bytes

    @classmethod
    def _create(cls, verified: _VerifiedLocalResult) -> Self:
        _, result = _family_result(verified)
        instance = object.__new__(cls)
        object.__setattr__(instance, "_verified", verified)
        object.__setattr__(instance, "_json_bytes", _canonical_local_result_bytes(result))
        return instance

    @property
    def family(self) -> str:
        """Return the exact local-neighborhood family."""
        family, _ = _family_result(self._verified)
        return family.value

    @property
    def completion(self) -> str:
        """Return complete, policy-stopped, or truncated search coverage."""
        result = self._verified_source()
        neighborhood = (
            result.neighborhood
            if isinstance(result, FoldbackNeighborhoodDiscoveryResult)
            else result.discovery
        )
        return neighborhood.disposition.completion.value

    @property
    def feasibility(self) -> str:
        """Return feasible, infeasible, or unknown existence status."""
        result = self._verified_source()
        neighborhood = (
            result.neighborhood
            if isinstance(result, FoldbackNeighborhoodDiscoveryResult)
            else result.discovery
        )
        return neighborhood.disposition.feasibility.value

    @property
    def termination_reason(self) -> str:
        """Return the exact reason the bounded search stopped."""
        result = self._verified_source()
        neighborhood = (
            result.neighborhood
            if isinstance(result, FoldbackNeighborhoodDiscoveryResult)
            else result.discovery
        )
        return neighborhood.disposition.termination_reason.value

    @property
    def problem_id(self) -> str:
        """Return molecular problem identity independent of execution bounds."""
        result = self._verified_source()
        neighborhood = (
            result.neighborhood
            if isinstance(result, FoldbackNeighborhoodDiscoveryResult)
            else result.discovery
        )
        return neighborhood.problem_id

    @property
    def result_id(self) -> str:
        """Return the sealed family-result identity."""
        return self._verified_source().result_id

    @property
    def realization_count(self) -> int:
        """Return the exact number of accepted local realizations."""
        return len(self._verified_source().realizations)

    @property
    def json_bytes(self) -> bytes:
        """Return canonical family-result JSON bytes."""
        return self._json_bytes

    def write(self, destination: str | Path) -> Path:
        """Atomically write the canonical result into a new directory."""
        output = Path(destination)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing local-neighborhood path: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            (staging / "result.json").write_bytes(self._json_bytes)
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return output

    def _verified_source(self) -> _LocalResult:
        _, result = _family_result(self._verified_authority())
        return result

    def _verified_authority(self) -> _VerifiedLocalResult:
        _, result = _family_result(self._verified)
        if _canonical_local_result_bytes(result) != self._json_bytes:
            raise ValueError("Local-neighborhood receipt content disagrees with its authority.")
        return self._verified

    def __repr__(self) -> str:
        return (
            f"LocalNeighborhoodDiscovery(family={self.family!r}, completion={self.completion!r}, "
            f"feasibility={self.feasibility!r}, "
            f"result_id={self.result_id!r})"
        )


def _load_request(path: str | Path) -> LocalNeighborhoodRequest:
    mapping = load_source_mapping(path, source_label="HOP local-neighborhood")
    if mapping.get("schema") != "hop.local-neighborhood-request/v5":
        raise ValueError(f"Unsupported HOP local-neighborhood schema: {mapping.get('schema')!r}.")
    request = LocalNeighborhoodRequest.model_validate_json(
        json.dumps(mapping, separators=(",", ":"))
    )
    _validate_local_execution_limits(
        max_search_nodes=request.search.max_search_nodes,
        max_realizations=request.search.max_realizations,
    )
    return request


def discover_local_neighborhood(source_path: str | Path) -> LocalNeighborhoodDiscovery:
    """Load one strict request and discover its bounded local neighborhood."""
    return _discover_request(_load_request(source_path))


def _discover_request(request: LocalNeighborhoodRequest) -> LocalNeighborhoodDiscovery:
    """Execute an already normalized request through the family authority."""
    if request.family is LocalNeighborhoodFamily.FOLDBACK:
        return LocalNeighborhoodDiscovery._create(
            verify_foldback_neighborhood_result(discover_foldback_neighborhood(request))
        )
    if request.family is LocalNeighborhoodFamily.BASAL:
        return LocalNeighborhoodDiscovery._create(
            verify_basal_neighborhood_result(discover_basal_neighborhood(request))
        )
    raise ValueError(f"Unsupported local-neighborhood family: {request.family!r}.")


def load_verified_local_neighborhood(result_path: str | Path) -> LocalNeighborhoodDiscovery:
    """Load one family result after exact deterministic discovery replay."""
    mapping = load_source_mapping(
        result_path,
        max_bytes=_LOCAL_RESULT_MAX_BYTES,
        source_label="HOP local-neighborhood result",
    )
    return _verify_result_mapping(mapping)


def _verify_result_mapping(mapping: dict[str, object]) -> LocalNeighborhoodDiscovery:
    """Replay the captured result mapping without reopening its source."""
    schema = mapping.get("schema")
    payload = json.dumps(mapping, separators=(",", ":"))
    if schema == "hop.foldback-neighborhood-result/v4":
        _validate_result_mapping_execution_limits(mapping, result_container="neighborhood")
        verified: _VerifiedLocalResult = verify_foldback_neighborhood_result(
            FoldbackNeighborhoodDiscoveryResult.model_validate_json(payload)
        )
    elif schema == "hop.basal-neighborhood-result/v5":
        _validate_result_mapping_execution_limits(mapping, result_container="discovery")
        verified = verify_basal_neighborhood_result(
            BasalNeighborhoodDiscoveryResult.model_validate_json(payload)
        )
    else:
        raise ValueError(f"Unsupported HOP local-neighborhood result schema: {schema!r}.")
    return LocalNeighborhoodDiscovery._create(verified)


__all__ = [
    "LocalNeighborhoodDiscovery",
    "discover_local_neighborhood",
    "load_verified_local_neighborhood",
]
