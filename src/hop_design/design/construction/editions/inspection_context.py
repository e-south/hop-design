"""Detached teaching facts for one member of an admitted, unfiltered edition."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class InspectionContext:
    """Keep shared context once and decode only the inspected preparation's row.

    These are metadata, not cached molecular authorities. Preserve record order
    and the first row for repeated identities, as the original projection did.
    Returned dictionaries are detached from both the input and retained bytes.
    """

    shared: bytes
    rows: Mapping[str, bytes]

    @classmethod
    def from_choices(cls, answer: dict[str, Any]) -> "InspectionContext":
        def encode(value: Any) -> bytes:
            return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()

        shared = {
            key: answer[key]
            for key in ("snapshot_digest", "axes", "context", "coverage")
            if key in answer
        }
        rows = {}
        for path in answer["paths"]:
            identity = path["materialized_realization_id"]
            if identity not in rows:
                rows[identity] = encode(path)
        return cls(encode(shared), MappingProxyType(rows))

    @property
    def bytes(self) -> int:
        """Serialized payload bytes; process RSS also includes mapping/key overhead."""
        return len(self.shared) + sum(map(len, self.rows.values()))

    def member(self, identity: str) -> dict[str, Any]:
        return {**json.loads(self.shared), "paths": [json.loads(self.rows[identity])]}
