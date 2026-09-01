"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/replay_admission.py

Records in-process construction results admitted by deterministic replay.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from weakref import WeakKeyDictionary

from hop_design.models.construction.complete import ConstructionSpaceResult
from hop_design.serialization import canonical_json_bytes, sha256_digest

_ADMITTED_RESULT_DIGESTS: WeakKeyDictionary[object, str] = WeakKeyDictionary()


def record_replay_admission(source: object, result: ConstructionSpaceResult) -> None:
    """Record the exact content admitted for one verified result container."""
    _ADMITTED_RESULT_DIGESTS[source] = sha256_digest(canonical_json_bytes(result))


def has_current_replay_admission(source: object, result: ConstructionSpaceResult) -> bool:
    """Return whether replay admitted this object with its current exact content."""
    admitted_digest = _ADMITTED_RESULT_DIGESTS.get(source)
    return admitted_digest is not None and admitted_digest == sha256_digest(
        canonical_json_bytes(result)
    )


__all__: list[str] = []
