"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/selection.py

Restricts complete composition to explicitly selected local realizations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.construction.complete.request import ConstructionDiscoveryRequest
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)


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


def validate_detailed_authority_ids(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackNeighborhoodDiscoveryResult,
    basal: BasalNeighborhoodDiscoveryResult | None,
) -> None:
    """Require detailed authority identities to equal the composition request."""
    if foldback.result_id != request.foldback_result_id:
        raise ValueError("Foldback detailed result identity does not match the request.")
    if (None if basal is None else basal.result_id) != request.basal_result_id:
        raise ValueError("Basal detailed result identity does not match the request.")


def select_local_domains(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackNeighborhoodDiscoveryResult,
    basal: BasalNeighborhoodDiscoveryResult | None,
) -> tuple[
    tuple[FoldbackLocalRealization, ...],
    tuple[BasalRealizationRecord | None, ...],
]:
    """Return exact payload-matched local domains under optional selections."""
    payload = request.payload.payload.sequence
    foldback_records = select_foldback_records(
        tuple(item for item in foldback.realizations if item.payload_sequence == payload),
        request.selected_foldback_realization_id,
    )
    basal_records = select_basal_records(
        (
            (None,)
            if basal is None
            else tuple(item for item in basal.realizations if item.payload_sequence == payload)
        ),
        request.selected_basal_realization_id,
    )
    return foldback_records, basal_records


__all__ = [
    "select_basal_records",
    "select_foldback_records",
    "select_local_domains",
    "validate_detailed_authority_ids",
]
