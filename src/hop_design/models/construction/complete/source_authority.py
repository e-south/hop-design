"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_authority.py

Validates complete-route membership in exact detailed local authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any

from hop_design.models.construction.accounting import SearchCompletionStatus
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)


def expected_upstream_truncation_reasons(
    *,
    request: Any,
    foldback: FoldbackNeighborhoodDiscoveryResult,
    basal: BasalNeighborhoodDiscoveryResult | None,
) -> tuple[str, ...]:
    """Return local-search truncation evidence relevant to complete composition."""
    if request.selects_local_realizations:
        return ()
    reasons = []
    for family, discovery in (
        ("foldback", foldback.neighborhood),
        *((("basal", basal.discovery),) if basal is not None else ()),
    ):
        if discovery.disposition.completion is not SearchCompletionStatus.COMPLETE:
            reasons.append(
                f"{family}:{discovery.disposition.termination_reason.value}"
            )
    return tuple(reasons)


def validate_local_authorities(
    *,
    foldback: FoldbackLocalRealization,
    foldback_realization_id: str,
    basal: BasalRealizationRecord | None,
    basal_realization_id: str | None,
    local_realization_ids: tuple[str, ...],
) -> None:
    """Require complete-route local IDs to equal embedded self-validating members."""
    FoldbackLocalRealization.model_validate(foldback.model_dump(mode="python"))
    if foldback.foldback_realization_id != foldback_realization_id:
        raise ValueError("Materialized route must embed its exact foldback authority.")
    if basal is not None:
        BasalRealizationRecord.model_validate(basal.model_dump(mode="python"))
    if (None if basal is None else basal.basal_realization_id) != basal_realization_id:
        raise ValueError("Materialized route must embed its exact basal authority.")
    expected_ids = (
        *((basal_realization_id,) if basal_realization_id is not None else ()),
        foldback_realization_id,
    )
    if local_realization_ids != expected_ids:
        raise ValueError("Complete route must preserve its exact ordered local authorities.")


def validate_result_authorities(
    *,
    request: Any,
    provenance: Any,
    foldback: FoldbackNeighborhoodDiscoveryResult,
    basal: BasalNeighborhoodDiscoveryResult | None,
    realizations: tuple[Any, ...],
) -> None:
    """Replay result domains and accepted members from detailed discovery authorities."""
    FoldbackNeighborhoodDiscoveryResult.model_validate(foldback.model_dump(mode="python"))
    if basal is not None:
        BasalNeighborhoodDiscoveryResult.model_validate(basal.model_dump(mode="python"))
    if foldback.result_id != request.foldback_result_id:
        raise ValueError("Result foldback authority must equal the requested detailed result.")
    if (None if basal is None else basal.result_id) != request.basal_result_id:
        raise ValueError("Result basal authority must equal the requested detailed result.")
    payload = request.payload.payload.sequence
    foldback_records = tuple(
        item for item in foldback.realizations if item.payload_sequence == payload
    )
    basal_records = (
        ()
        if basal is None
        else tuple(item for item in basal.realizations if item.payload_sequence == payload)
    )
    foldback_members = (
        (request.selected_foldback_realization_id,)
        if request.selected_foldback_realization_id is not None
        else tuple(item.foldback_realization_id for item in foldback_records)
    )
    basal_members = (
        (request.selected_basal_realization_id,)
        if request.selected_basal_realization_id is not None
        else tuple(item.basal_realization_id for item in basal_records)
    )
    foldback_member_set = {record.foldback_realization_id for record in foldback_records}
    basal_member_set = {record.basal_realization_id for record in basal_records}
    if any(item not in foldback_member_set for item in foldback_members):
        raise ValueError("Selected foldback authority must belong to the detailed result.")
    if any(item not in basal_member_set for item in basal_members):
        raise ValueError("Selected basal authority must belong to the detailed result.")
    if (
        provenance.foldback_realization_ids != foldback_members
        or provenance.basal_realization_ids != basal_members
    ):
        raise ValueError("Construction provenance domains must derive from detailed authorities.")
    foldback_by_id = {item.foldback_realization_id: item for item in foldback_records}
    basal_by_id = {item.basal_realization_id: item for item in basal_records}
    for realization in realizations:
        if foldback_by_id.get(realization.foldback_realization_id) != (
            realization.foldback_authority
        ):
            raise ValueError("Accepted foldback member must equal its detailed result authority.")
        expected_basal = (
            None
            if realization.basal_realization_id is None
            else basal_by_id.get(realization.basal_realization_id)
        )
        if expected_basal is None and realization.basal_realization_id is not None:
            raise ValueError("Accepted basal member must belong to its detailed result authority.")
        if realization.basal_authority != expected_basal:
            raise ValueError("Accepted basal member must equal its detailed result authority.")


__all__ = [
    "expected_upstream_truncation_reasons",
    "validate_local_authorities",
    "validate_result_authorities",
]
