"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/selection_reference.py

Creates and validates stable references to accepted construction realizations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.publication import publish_file_create_only
from hop_design.models.construction.selection import ConstructionSelectionRecord
from hop_design.serialization import canonical_json_bytes

from .complete.bundle import ConstructionCompilation, VerifiedConstructionBundle

_SELECTION_MAX_BYTES = 16_384


def _require_json_path(path: Path) -> None:
    if path.suffix != ".json":
        raise ValueError("Construction selection paths must use the .json extension.")


def _verified_receipt(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> ConstructionCompilation | VerifiedConstructionBundle:
    if not isinstance(receipt, ConstructionCompilation | VerifiedConstructionBundle):
        raise TypeError("Construction selection requires a verified construction receipt.")
    receipt._verified_source()
    return receipt


def _bind_selection(
    record: ConstructionSelectionRecord,
    *,
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> ConstructionSelectionRecord:
    verified = _verified_receipt(receipt)
    if record.source_result_id != verified.result_id:
        raise ValueError(
            "Construction selection does not belong to this verified construction result."
        )
    if record.materialized_realization_id not in verified.materialized_realization_ids:
        raise ValueError(
            "Construction selection is not an accepted realization in the verified result."
        )
    return record


@dataclass(frozen=True, init=False, repr=False)
class ConstructionSelection:
    """Opaque non-authoritative reference to one accepted construction realization."""

    _record: ConstructionSelectionRecord
    _json_bytes: bytes

    @classmethod
    def _create(cls, record: ConstructionSelectionRecord) -> Self:
        verified = ConstructionSelectionRecord.model_validate(
            record.model_dump(mode="python", by_alias=True)
        )
        instance = object.__new__(cls)
        object.__setattr__(instance, "_record", verified)
        object.__setattr__(instance, "_json_bytes", canonical_json_bytes(verified))
        return instance

    @property
    def schema_id(self) -> str:
        """Return the selection document schema."""
        return self._record.schema_id

    @property
    def source_result_id(self) -> str:
        """Return the verified construction result that owns the realization."""
        return self._record.source_result_id

    @property
    def materialized_realization_id(self) -> str:
        """Return the explicitly selected accepted realization identity."""
        return self._record.materialized_realization_id

    @property
    def json_bytes(self) -> bytes:
        """Return canonical non-authoritative selection JSON."""
        return self._json_bytes

    def write(self, destination: str | Path, *, protected_root: str | Path | None = None) -> Path:
        """Atomically write the selection to exactly one new file path."""
        output = Path(destination)
        _require_json_path(output)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing selection path: {output}")
        publish_file_create_only(
            self._json_bytes,
            output,
            protected_root=None if protected_root is None else Path(protected_root),
        )
        return output

    def __repr__(self) -> str:
        return (
            f"ConstructionSelection(source_result_id={self.source_result_id!r}, "
            f"materialized_realization_id={self.materialized_realization_id!r})"
        )


def select_construction_realization(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
    *,
    materialized_realization_id: str,
) -> ConstructionSelection:
    """Reference one accepted realization without changing result authority."""
    verified = _verified_receipt(receipt)
    record = ConstructionSelectionRecord(
        source_result_id=verified.result_id,
        materialized_realization_id=materialized_realization_id,
    )
    return ConstructionSelection._create(_bind_selection(record, receipt=verified))


def load_construction_selection(
    selection_path: str | Path,
    *,
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> ConstructionSelection:
    """Load one selection and bind it to its verified construction result."""
    verified = _verified_receipt(receipt)
    _require_json_path(Path(selection_path))
    mapping = load_source_mapping(
        selection_path,
        max_bytes=_SELECTION_MAX_BYTES,
        source_label="HOP construction selection",
    )
    try:
        record = ConstructionSelectionRecord.model_validate_json(
            json.dumps(mapping, separators=(",", ":"))
        )
    except Exception as error:
        raise ValueError(f"Construction selection is invalid: {error}") from error
    return ConstructionSelection._create(_bind_selection(record, receipt=verified))


__all__ = [
    "ConstructionSelection",
    "load_construction_selection",
    "select_construction_realization",
]
