"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/execution/coverage.py

Describes recorded local-search coverage for execution, continuation and family admission.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from typing import Literal, TypedDict

from ..local_public import LocalNeighborhoodDiscovery


class LocalCoverage(TypedDict):
    completion: str
    feasibility: str
    termination_reason: str
    realization_count: int
    result_id: str
    rejection_counts: dict[str, int]


class LocalStop(TypedDict):
    stage: str
    scope: Literal["local_domain"]
    status: Literal["selection-required", "infeasible", "unresolved"]
    accepted: Literal[0]
    result_id: None
    rejection_reasons: list[str]


def describe_local_stop(coverage: LocalCoverage, family: str) -> LocalStop | None:
    """Describe a sole-witness stop; one recorded witness permits continuation."""
    if coverage["realization_count"] == 1:
        return None
    return {
        "stage": family,
        "scope": "local_domain",
        "status": (
            "selection-required"
            if coverage["realization_count"] > 1
            else "infeasible"
            if coverage["feasibility"] == "infeasible"
            else "unresolved"
        ),
        "accepted": 0,
        "result_id": None,
        "rejection_reasons": sorted(coverage["rejection_counts"]),
    }


def describe_local_coverage(local: LocalNeighborhoodDiscovery, family: str) -> LocalCoverage:
    local_result = json.loads(local.json_bytes)
    local_rejections = {
        item["code"]: item["count"]
        for item in local_result["neighborhood" if family == "foldback" else "discovery"][
            "failure_reasons"
        ]
    }
    return {
        "completion": local.completion,
        "feasibility": local.feasibility,
        "termination_reason": local.termination_reason,
        "realization_count": local.realization_count,
        "result_id": local.result_id,
        "rejection_counts": local_rejections,
    }
