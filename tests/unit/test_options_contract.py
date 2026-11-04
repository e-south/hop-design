"""Reject contradictory intent and invalid resource limits before molecular work."""

import json

import pytest

from hop_design.design.construction.options.limits import (
    MAX_BYTES,
    MAX_FILES,
    require_inventory_size,
)
from hop_design.design.construction.options.records import require_budget
from hop_design.models.construction.options import ScaffoldComparisonRequest


@pytest.mark.parametrize("budget", [True, 0, 65, 1.0, "1", None])
def test_continuation_bound_is_explicit_and_strict(budget):
    with pytest.raises(ValueError, match="explicit integer"):
        require_budget(budget)


@pytest.mark.parametrize("count,size", [(MAX_FILES + 1, 0), (1, MAX_BYTES + 1)])
def test_packet_capture_is_bounded(count, size):
    with pytest.raises(ValueError, match="packet bound"):
        require_inventory_size(count, size)


@pytest.mark.parametrize("edit", ["shared", "duplicate", "unknown", "mismatched", "coerced"])
def test_comparison_requires_distinct_and_noncontradictory_members(edit):
    value = {
        "schema": "hop.scaffold-comparison/v1",
        "members": [
            {"name": "loop3", "dimensions": {"loop_nt": 3}},
            {"name": "loop4", "dimensions": {"loop_nt": 4}},
        ],
        "shared_properties": ["non_loop_sequences"],
    }
    if edit == "shared":
        value["shared_properties"].append("loop_nt")
    elif edit == "duplicate":
        value["members"][1]["dimensions"]["loop_nt"] = 3
    elif edit == "unknown":
        value["members"][1]["dimensions"] = {"loop_radius": 4}
    elif edit == "mismatched":
        value["members"][1]["dimensions"] = {"loop_side_paired_bp": 4}
    else:
        value["members"][1]["dimensions"]["loop_nt"] = "4"
    with pytest.raises(ValueError):
        ScaffoldComparisonRequest.model_validate_json(json.dumps(value))
