"""The batching boundary never hides an unresolved local or failed whole attempt."""

import json
from types import SimpleNamespace

import pytest

from hop_design.design.construction.surveys import evaluate
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


@pytest.mark.parametrize("terminal", ["unresolved_local", "failed_whole", "supported"])
def test_batch_stops_at_first_nonempty_or_unresolved_attempt(monkeypatch, terminal):
    visited = []
    stored = []
    index = SimpleNamespace(put_object=stored.append)
    budget = SurveyEvaluationLimits(
        local_nodes=1,
        local_realizations=1,
        release_site_pairs=1,
        continuation_batch_size=8,
    )

    def attempt(_index, _locals, _branches, _limits, *, target, address):
        branch = address["branch"]
        visited.append(branch)
        assert branch <= 1, "Batch traversed past a nonempty or unresolved attempt"
        record = {
            "branch": branch,
            "page": 0,
            "pair": 0,
            "local_coverage": {},
            "navigation_nodes": 3 + branch,
            "rejection": None,
            "next": {"branch": branch + 1},
            "exhaustion_proven": terminal != "unresolved_local",
            "witnesses": ["complete"] if terminal == "supported" and branch == 1 else [],
        }
        return record, str(branch).encode(), branch == 0

    monkeypatch.setattr(evaluate, "_evaluate_one", attempt)
    branches = SurveyBranches(
        InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    )
    result = evaluate.evaluate_step(index, None, branches, budget, target=0, address={"branch": 0})
    assert visited == [0, 1]
    assert stored == [b"1"]
    assert result["branch"] == 1
    assert len(result["skipped_empty"]) == 1
    assert result["skipped_empty"][0]["navigation_nodes"] == 3
    assert result["navigation_nodes"] == 7
    assert result["navigation_nodes_complete"] is True
