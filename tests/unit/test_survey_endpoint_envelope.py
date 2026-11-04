"""A short branch representative cannot exclude longer permitted completions."""

import json

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.completion.population import condition_population
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.models.construction.surveys.execution import (
    DEFAULT_SEQUENCE_LIMITS,
    SurveyEvaluationLimits,
)
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.support.context_completion import policy, request


def test_candidate_pages_use_the_whole_envelope_across_context_branches(tmp_path):
    path = request(tmp_path, "long-completion", completion=True)
    data = json.loads(path.read_text())
    data["basal"]["annealing_lengths_nt"] = [40]
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = {
        "min_length_nt": 14,
        "max_length_nt": 24,
        "base_spec": "N",
    }
    authored = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    branches = SurveyBranches(authored)
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=100)
    first = branches.product(0, branch=0, limits=limits)
    local = PartitionPlans().get(first).basal
    assert local.parts > 0
    assert (
        condition_population(
            first, local, policy("N" * 14), DEFAULT_SEQUENCE_LIMITS
        ).population.parts
        == 0
    )
    with SurveyIndex.create(
        tmp_path / "index.sqlite", request=authored, producer={"test": "endpoint-envelope"}
    ) as index:
        plans = PartitionPlans(index)
        admitted = plans.get(first)
        assert admitted.basal_candidates.parts > 0
        assert not admitted.empty_candidates
        # An exact context at another ordinary branch must use the same page map.
        last = branches.product(
            0, branch=(branches.context_count - 1) * branches.geometry_count, limits=limits
        )
        other = plans.get(last)
        assert admitted.count == other.count
        for page in (0, admitted.count - 1):
            left = admitted.product(first, page).basal.search.sequence_partition
            right = other.product(last, page).basal.search.sequence_partition
            assert left == right
