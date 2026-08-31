"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/selection.py

Restricts complete composition to explicitly selected local realizations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization


def select_foldback_records(
    records: tuple[FoldbackLocalRealization, ...],
    realization_id: str | None,
) -> tuple[FoldbackLocalRealization, ...]:
    """Return the complete foldback domain or one exact selected member."""
    if realization_id is None:
        return records
    selected = tuple(item for item in records if item.foldback_realization_id == realization_id)
    if len(selected) != 1:
        raise ValueError("The selected foldback realization was not found exactly once.")
    return selected


def select_basal_records(
    records: tuple[BasalRealizationRecord | None, ...],
    realization_id: str | None,
) -> tuple[BasalRealizationRecord | None, ...]:
    """Return the complete basal domain or one exact selected member."""
    if realization_id is None:
        return records
    selected = tuple(
        item for item in records if item is not None and item.basal_realization_id == realization_id
    )
    if len(selected) != 1:
        raise ValueError("The selected basal realization was not found exactly once.")
    return selected


__all__ = ["select_basal_records", "select_foldback_records"]
