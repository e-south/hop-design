"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/loading.py

Loads strict versioned design specifications from safe local files.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path

from hop_design.models.spec import DesignSpec, HopSpec, ResolvedHopSpec

from .source_documents import SourceDocumentLimitError, load_source_mapping

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
    try:
        payload = load_source_mapping(path, max_bytes=max_bytes, source_label="HOP spec")
    except SourceDocumentLimitError as error:
        raise SpecSourceLimitError(actual=error.actual, max_bytes=error.max_bytes) from error
    schema = payload.get("schema")
    encoded = json.dumps(payload, separators=(",", ":"))
    if schema == "hop.design/v2":
        return HopSpec.model_validate_json(encoded)
    if schema == "hop.resolved-design/v2":
        return ResolvedHopSpec.model_validate_json(encoded)
    raise ValueError(f"Unsupported HOP spec schema: {schema!r}.")


__all__ = ["DEFAULT_SPEC_MAX_BYTES", "SpecSourceLimitError", "load_spec"]
