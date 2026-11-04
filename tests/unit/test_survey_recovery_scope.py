"""Recover conditioned survey addresses without writing to the saved index."""

import json

import pytest

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document

LIMITS = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=100)


def request():
    data = survey_document()
    data["source_context_objective"] = "paired_scaffold_completions"
    data["placements"] = [{"left_bp": 6, "right_bp": 6}]
    data["basal"]["annealing_lengths_nt"] = [20]
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "N" * 14
    )
    return InterfaceSurveyRequest.model_validate_json(json.dumps(data))


def test_request_only_recovery_keeps_the_endpoint_conditioned_candidate_domain():
    scope = request()
    product = SurveyBranches(scope).product(0, branch=0, limits=LIMITS)
    ordinary = PartitionPlans(limits=LIMITS.sequence_space_limits).get(product)
    recovered = PartitionPlans(request=scope, limits=LIMITS.sequence_space_limits).get(product)
    assert ordinary.endpoint is None
    assert recovered.endpoint is not None
    assert recovered.endpoint.facts()["scope"] == "necessary_endpoint_admission"
    assert recovered.count > 0


def test_index_and_request_cannot_disagree(tmp_path):
    scope = request()
    with (
        SurveyIndex.create(tmp_path / "index.sqlite", request=scope, producer={}) as index,
        pytest.raises(ValueError, match="request"),
    ):
        PartitionPlans(index, request=scope.model_copy(update={"name": "different"}))


def test_frame_wrapper_rejects_foreign_request_and_replaces_changed_limits():
    scope = request()
    branches = SurveyBranches(scope)
    plans = PartitionPlans(request=scope, limits=LIMITS.sequence_space_limits)
    geometry = (0,) * 6
    first = plans.frame_admission(branches, LIMITS, 0, geometry)
    old = plans._basal_admissions
    changed = LIMITS.model_copy(update={"local_nodes": LIMITS.local_nodes + 1})
    assert plans.frame_admission(branches, changed, 0, geometry) == first
    assert plans._basal_admissions is not old
    foreign = SurveyBranches(scope.model_copy(update={"name": "different"}))
    with pytest.raises(ValueError, match="request"):
        plans.frame_admission(foreign, changed, 0, geometry)
