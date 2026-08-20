"""Canonical serialization used for content addressing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical_json_bytes(value: BaseModel | Any) -> bytes:
    """Serialize a model or JSON value deterministically with one trailing newline."""
    data = value.model_dump(mode="json", by_alias=True) if isinstance(value, BaseModel) else value
    return (
        json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        + b"\n"
    )


def sha256_digest(content: bytes) -> str:
    """Return a tagged SHA-256 digest."""
    return f"sha256:{hashlib.sha256(content).hexdigest()}"
