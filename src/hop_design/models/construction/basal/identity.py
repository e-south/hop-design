"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal/identity.py

Calculates content identity for exact basal construction evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, cast

from hop_design.models.base import HopModel
from hop_design.serialization import canonical_json_bytes, sha256_digest


def basal_realization_id(record: HopModel) -> str:
    """Return molecular identity independent of enzyme procurement metadata."""
    seed = record.model_dump(mode="json", exclude={"basal_realization_id"})
    definitions = cast(list[dict[str, Any]], seed["enzyme_definitions"])
    for definition in definitions:
        enzyme = cast(dict[str, Any], definition["enzyme"])
        enzyme["vendor_metadata"] = []
    digest = sha256_digest(canonical_json_bytes(seed)).removeprefix("sha256:")
    return f"hop:basal-realization/{digest}@1"
