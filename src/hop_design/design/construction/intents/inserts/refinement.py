"""Stage-preserving filters over replayed insert witnesses and their existing plot facts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...variants.refinement import refine_options
from .admission import admitted_options

if TYPE_CHECKING:
    from ..results import InsertDesignChoices


def validate_reference(choices: InsertDesignChoices, query: DesignRefinementQuery) -> None:
    if (
        query.reference.request_digest
        != sha256_digest(canonical_json_bytes(choices._pool._request))
        or query.reference.snapshot_digest != choices._pool._digest
    ):
        raise ValueError("Preservation reference belongs to a different discovery or snapshot.")
    if not any(
        p["materialized_realization_id"] == query.reference.materialized_realization_id
        for p in choices._pool.query()["paths"]
    ):
        raise ValueError("Preservation reference is not a complete preparation in this snapshot.")


def refine_result(
    choices: InsertDesignChoices, result: dict[str, Any], query: DesignRefinementQuery
) -> dict[str, Any]:
    return refine_options(
        result,
        query,
        admitted_options(choices),
        validation="complete_comparison_witnesses_replayed",
    )
