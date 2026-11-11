"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/verification.py

Admits local construction results after deterministic discovery replay.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from hop_design.design.runtime import creation_version, producer_identity
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.serialization import canonical_json_bytes

from .basal.discovery import discover_basal_neighborhood
from .foldback.discovery import discover_foldback_neighborhood

_proofs: ContextVar[set[tuple[bytes, bytes]] | None] = ContextVar(
    "local_replay_proofs", default=None
)


@contextmanager
def local_replay_scope() -> Iterator[None]:
    """Reuse exact local proofs within one admission; never retain them across loads."""
    token = _proofs.set(set())
    try:
        yield
    finally:
        _proofs.reset(token)


def _proof_key(kind: str, content: bytes) -> tuple[bytes, bytes] | None:
    if _proofs.get() is None:
        return None
    return (
        canonical_json_bytes(["local-replay/v2", kind, producer_identity(), creation_version()]),
        content,
    )


def _remember(key: tuple[bytes, bytes] | None) -> None:
    proofs = _proofs.get()
    if (
        key is not None
        and proofs is not None
        and len(proofs) < 64
        and sum(len(p[0]) + len(p[1]) for p in proofs) + len(key[0]) + len(key[1]) <= 8_388_608
    ):
        proofs.add(key)


class ConstructionVerificationError(ValueError):
    """Raised when deterministic construction discovery replay disagrees."""


@dataclass(frozen=True)
class VerifiedFoldbackNeighborhoodResult:
    """Foldback result admitted after exact deterministic discovery replay."""

    result: FoldbackNeighborhoodDiscoveryResult
    _canonical_bytes: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        result = _replay_foldback_result(self.result)
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "_canonical_bytes", canonical_json_bytes(result))

    def _verified_result(self) -> FoldbackNeighborhoodDiscoveryResult:
        if not hasattr(self, "_canonical_bytes") or (
            canonical_json_bytes(self.result) != self._canonical_bytes
        ):
            raise ConstructionVerificationError(
                "Foldback neighborhood result disagrees with deterministic discovery replay."
            )
        return self.result


@dataclass(frozen=True)
class VerifiedBasalNeighborhoodResult:
    """Basal result admitted after exact deterministic discovery replay."""

    result: BasalNeighborhoodDiscoveryResult
    _canonical_bytes: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        result = _replay_basal_result(self.result)
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "_canonical_bytes", canonical_json_bytes(result))

    def _verified_result(self) -> BasalNeighborhoodDiscoveryResult:
        if not hasattr(self, "_canonical_bytes") or (
            canonical_json_bytes(self.result) != self._canonical_bytes
        ):
            raise ConstructionVerificationError(
                "Basal neighborhood result disagrees with deterministic discovery replay."
            )
        return self.result


def _replay_foldback_result(
    result: FoldbackNeighborhoodDiscoveryResult,
) -> FoldbackNeighborhoodDiscoveryResult:
    parsed = FoldbackNeighborhoodDiscoveryResult.model_validate(result.model_dump(mode="python"))
    content = canonical_json_bytes(parsed)
    key = _proof_key("foldback", content)
    if key is not None and key in (_proofs.get() or ()):
        return parsed
    expected = discover_foldback_neighborhood(parsed.neighborhood.request)
    if canonical_json_bytes(expected) != content:
        raise ConstructionVerificationError(
            "Foldback neighborhood result disagrees with deterministic discovery replay."
        )
    _remember(key)
    return parsed


def _replay_basal_result(
    result: BasalNeighborhoodDiscoveryResult,
) -> BasalNeighborhoodDiscoveryResult:
    parsed = BasalNeighborhoodDiscoveryResult.model_validate(result.model_dump(mode="python"))
    content = canonical_json_bytes(parsed)
    key = _proof_key("basal", content)
    if key is not None and key in (_proofs.get() or ()):
        return parsed
    expected = discover_basal_neighborhood(parsed.discovery.request)
    if canonical_json_bytes(expected) != content:
        raise ConstructionVerificationError(
            "Basal neighborhood result disagrees with deterministic discovery replay."
        )
    _remember(key)
    return parsed


def verify_foldback_neighborhood_result(
    result: FoldbackNeighborhoodDiscoveryResult,
) -> VerifiedFoldbackNeighborhoodResult:
    """Rerun the exact foldback request and admit only canonical-byte equality."""
    return VerifiedFoldbackNeighborhoodResult(result=result)


def verify_basal_neighborhood_result(
    result: BasalNeighborhoodDiscoveryResult,
) -> VerifiedBasalNeighborhoodResult:
    """Rerun the exact basal request and admit only canonical-byte equality."""
    return VerifiedBasalNeighborhoodResult(result=result)


__all__ = [
    "ConstructionVerificationError",
    "VerifiedBasalNeighborhoodResult",
    "VerifiedFoldbackNeighborhoodResult",
    "verify_basal_neighborhood_result",
    "verify_foldback_neighborhood_result",
]
