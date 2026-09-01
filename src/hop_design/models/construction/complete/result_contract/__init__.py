"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/result_contract/__init__.py

Exports complete-construction result identity and replay contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from .identity import construction_space_result_id
from .materialized import (
    validate_endpoint_evidence,
    validate_materialized_evaluation,
    validate_materialized_request,
)
from .replay import (
    composition_truncation_reason,
    expected_accounting,
    expected_material_accounting,
    validate_combination_evaluations,
)

__all__ = [
    "composition_truncation_reason",
    "construction_space_result_id",
    "expected_accounting",
    "expected_material_accounting",
    "validate_combination_evaluations",
    "validate_endpoint_evidence",
    "validate_materialized_evaluation",
    "validate_materialized_request",
]
