"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/result_contract/identity.py

Derives complete-construction result identity from canonical authority facts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any

from hop_design.models.construction.payload import _content_id


def construction_space_result_id(result: Any) -> str:
    """Return the content identity for one complete-construction result."""
    content = {
        "schema": result.schema_id,
        "problem_id": result.problem_id,
        "execution_id": result.execution_id,
        "status": result.status,
        "realization_ids": tuple(item.materialized_realization_id for item in result.realizations),
        "geometry_groups": tuple(item.model_dump(mode="json") for item in result.geometry_groups),
        "final_product_groups": tuple(
            item.model_dump(mode="json") for item in result.final_product_groups
        ),
        "accounting": result.accounting.model_dump(mode="json"),
        "failure_reasons": tuple(item.model_dump(mode="json") for item in result.failure_reasons),
        "truncation_reasons": result.truncation_reasons,
        "upstream_truncation_reasons": result.upstream_truncation_reasons,
        "provenance": result.provenance.model_dump(mode="json"),
        "material_accounting": result.material_accounting.model_dump(mode="json"),
        "claim_boundary": result.claim_boundary.model_dump(mode="json"),
        "combination_dispositions": tuple(
            item.model_dump(mode="json") for item in result.combination_dispositions
        ),
    }
    if result.source_partition_rejection_candidates:
        content["source_partition_rejection_candidate_ids"] = tuple(
            item.materialized_realization_id
            for item in result.source_partition_rejection_candidates
        )
    return _content_id("construction-space-result", 1, content)


__all__ = ["construction_space_result_id"]
