"""Strict JSON and YAML specification loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from hop_design.models.spec import DesignSpec, HopSpec, ResolvedHopSpec

DEFAULT_SPEC_MAX_BYTES = 1_000_000


class SpecSourceLimitError(ValueError):
    """Raised before decoding when a spec file exceeds its declared byte limit."""

    def __init__(self, *, actual: int, max_bytes: int) -> None:
        self.actual = actual
        self.max_bytes = max_bytes
        super().__init__(f"HOP spec max_bytes exceeded: {actual} > {max_bytes}.")


def load_spec(
    path: str | Path,
    *,
    max_bytes: int = DEFAULT_SPEC_MAX_BYTES,
) -> DesignSpec:
    """Load one known HOP schema without guessing from its fields."""
    source = Path(path)
    suffix = source.suffix.lower()
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1.")
    if source.is_symlink():
        raise ValueError("HOP spec source must not be a symlink.")
    if not source.is_file():
        raise ValueError(f"HOP spec source is not a regular file: {source}.")
    size_bytes = source.stat().st_size
    if size_bytes > max_bytes:
        raise SpecSourceLimitError(actual=size_bytes, max_bytes=max_bytes)
    text = source.read_text(encoding="utf-8")
    payload: Any
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        raise ValueError("HOP spec file extension must be .json, .yaml, or .yml.")
    if not isinstance(payload, dict):
        raise ValueError("HOP spec document root must be a mapping.")
    schema = payload.get("schema")
    encoded = json.dumps(payload, separators=(",", ":"))
    if schema == "hop.design/v1":
        return HopSpec.model_validate_json(encoded)
    if schema == "hop.resolved-design/v1":
        return ResolvedHopSpec.model_validate_json(encoded)
    raise ValueError(f"Unsupported HOP spec schema: {schema!r}.")


__all__ = ["DEFAULT_SPEC_MAX_BYTES", "SpecSourceLimitError", "load_spec"]
