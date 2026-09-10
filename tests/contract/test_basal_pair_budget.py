"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_basal_pair_budget.py

Tests aggregate noncanonical-pair constraints in basal search and replay.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from pathlib import Path

import pytest
import yaml

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.models.construction import (
    BasalGeometryDomain,
    BasalTarget,
    LocalNeighborhoodRequest,
)
from hop_design.models.construction.basal import BasalRealizationRecord


def _request(end: str, cap: int | None) -> LocalNeighborhoodRequest:
    content = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "examples/basal-junction/request.yaml").read_text()
    )
    domain = content["geometry_domain"]
    domain.update(nick_strand="top", nick_offsets_nt=[0])
    domain["future_release"]["cohesive_end_sequence"] = end
    for pair in domain["pairing_constraints"][1:]:
        pair["allowed_class"] = "any"
    if cap is not None:
        domain["max_noncanonical_pairs"] = cap
    return LocalNeighborhoodRequest.model_validate_json(json.dumps(content))


@pytest.mark.parametrize(
    ("end", "cap", "feasible"),
    (("AAAA", 2, False), ("TCTA", 2, False), ("ATAA", 2, True), ("CTCA", 0, True)),
)
def test_budget_constrains_search_including_gt_wobble(end, cap, feasible):
    result = discover_basal_neighborhood(_request(end, cap))
    assert result.discovery.disposition.completion.value == "complete"
    assert bool(result.realizations) is feasible
    if feasible:
        assert all(
            sum(p.pair_class.value != "match" for p in r.projection.pairing_state.pairs) <= cap
            for r in result.realizations
        )
        assert all(
            r.local_realization.achieved_geometry.max_noncanonical_pairs == cap
            for r in result.realizations
        )
    else:
        assert result.discovery.disposition.feasibility.value == "infeasible"
        assert any(f.code == "basal-pair-budget-exceeded" for f in result.discovery.failure_reasons)


def test_absent_budget_does_not_silently_restrict_a_request():
    request = _request("TCTA", None)
    assert "max_noncanonical_pairs" not in request.model_dump_json()
    result = discover_basal_neighborhood(request)
    pairs = result.realizations[0].projection.pairing_state.pairs
    assert [p.pair_class.value for p in pairs] == ["match", "mismatch", "wobble", "mismatch"]


@pytest.mark.parametrize("model", (BasalGeometryDomain, BasalTarget))
@pytest.mark.parametrize("cap", (-1, True, 1.5))
def test_pair_budget_rejects_invalid_counts(model, cap):
    data = _request("CTCA", None).geometry_domain.model_dump(mode="json")
    if model is BasalTarget:
        data = next(_request("CTCA", None).geometry_domain.exact_targets()).model_dump(mode="json")
    data["max_noncanonical_pairs"] = cap
    with pytest.raises(ValueError):
        model.model_validate_json(json.dumps(data))


def test_intrinsic_replay_rejects_a_resealed_over_budget_realization():
    record = discover_basal_neighborhood(_request("TCTA", None)).realizations[0]
    local = record.local_realization
    geometry = local.achieved_geometry.model_dump(mode="json")
    geometry["max_noncanonical_pairs"] = 2
    constrained = BasalTarget.model_validate_json(json.dumps(geometry))
    # Local identities must be recomputed so the test reaches molecular validation.
    local_content = {
        name: getattr(local, name)
        for name in type(local).model_fields
        if name != "local_realization_id"
    }
    local_content.update(achieved_geometry=constrained)
    changed = type(local).create(**local_content)
    content = {
        name: getattr(record, name)
        for name in type(record).model_fields
        if name != "basal_realization_id"
    }
    content["local_realization"] = changed
    with pytest.raises(ValueError, match="noncanonical-pair budget"):
        BasalRealizationRecord.create(**content)
