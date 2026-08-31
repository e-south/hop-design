"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_complete_construction_source_partition_binding.py

Tests complete-route selection of one replay-verified source partition.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    SourcePartitionBinding,
)
from tests.contract.test_complete_construction_contracts import _request


def _partition_bound_request() -> ConstructionDiscoveryRequest:
    mapping = _request(ConstructionEndpoint.SSDNA_HAIRPIN).model_dump(
        mode="python",
        by_alias=True,
    )
    mapping["source_partition_result_id"] = "hop:source-partition-result/" + "a" * 64 + "@1"
    mapping["selected_source_partition_realization_id"] = (
        "hop:source-partition-realization/" + "b" * 64 + "@1"
    )
    return ConstructionDiscoveryRequest.model_validate(mapping)


def test_selected_source_partition_is_an_explicit_problem_identity_constraint() -> None:
    baseline = _request(ConstructionEndpoint.SSDNA_HAIRPIN)
    selected = _partition_bound_request()

    assert selected.source_partition_result_id.endswith("a" * 64 + "@1")
    assert selected.selected_source_partition_realization_id.endswith("b" * 64 + "@1")
    assert selected.problem_id != baseline.problem_id
    assert selected.request_id != baseline.request_id


@pytest.mark.parametrize(
    "missing_field",
    ("source_partition_result_id", "selected_source_partition_realization_id"),
)
def test_source_partition_result_and_selected_member_are_copresent(
    missing_field: str,
) -> None:
    mapping = _partition_bound_request().model_dump(mode="python", by_alias=True)
    mapping.pop(missing_field)

    with pytest.raises(ValidationError, match="source partition"):
        ConstructionDiscoveryRequest.model_validate(mapping)


def test_source_partition_binding_seals_exact_route_state_references() -> None:
    content = {
        "result_id": "hop:source-partition-result/" + "a" * 64 + "@1",
        "realization_id": "hop:source-partition-realization/" + "b" * 64 + "@1",
        "source_preparation_product_state_id": ("hop:construction-state/" + "c" * 64 + "@1"),
        "top_material_use_id": "hop:material-use/" + "d" * 64 + "@1",
        "bottom_material_use_id": "hop:material-use/" + "e" * 64 + "@1",
        "reaction_program_id": "complete-route-example",
        "denatured_state_id": "hop:construction-state/" + "f" * 64 + "@1",
        "selected_state_id": "hop:construction-state/" + "0" * 64 + "@1",
    }

    binding = SourcePartitionBinding.create(**content)

    assert binding == SourcePartitionBinding.create(**content)
    assert binding.binding_id.startswith("hop:source-partition-binding/")
    with pytest.raises(ValidationError, match="identity"):
        SourcePartitionBinding.model_validate(
            {**binding.model_dump(mode="python"), "reaction_program_id": "forged-program"}
        )
