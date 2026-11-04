"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/result_contract/composition.py

Coordinates combination replay and selected source-partition validation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..evaluation import CompositionRejectionCode
from ..source_partition.plan import selected_partition_plan
from ..source_partition.result_validation import validate_source_partition_result_contract
from .materialized import validate_materialized_request
from .replay import validate_combination_evaluations

if TYPE_CHECKING:
    from ..result import ConstructionSpaceResult


def validate_composition_replay(result: ConstructionSpaceResult) -> None:
    """Distinguish input-derived rejection from rejection of a materialized candidate."""
    plan = selected_partition_plan(
        result.source_partition_authority,
        result.request.selected_source_partition_realization_id,
    )
    for disposition, candidate in zip(
        (
            d
            for d in result.combination_dispositions
            if d.rejection_reason is CompositionRejectionCode.HAIRPIN_SCAFFOLD_OUTSIDE_REQUEST
        ),
        result.scaffold_rejection_candidates,
        strict=True,
    ):
        validate_materialized_request(
            request=result.request,
            provenance=result.provenance,
            disposition=disposition,
            realization=candidate,
        )
    early_rejections = validate_combination_evaluations(
        request=result.request,
        foldback_authority=result.foldback_authority,
        basal_authority=result.basal_authority,
        dispositions=result.combination_dispositions,
        realizations=result.realizations,
        source_partition_rejection_candidates=result.source_partition_rejection_candidates,
        scaffold_rejection_candidates=result.scaffold_rejection_candidates,
        source_partition_plan=plan,
    )
    validate_source_partition_result_contract(
        request=result.request,
        provenance=result.provenance,
        authority=result.source_partition_authority,
        realizations=(*result.realizations, *result.scaffold_rejection_candidates),
        rejection_candidates=result.source_partition_rejection_candidates,
        dispositions=result.combination_dispositions,
        foldback_authority=result.foldback_authority,
        basal_authority=result.basal_authority,
        early_rejection_ordinals=early_rejections,
    )
