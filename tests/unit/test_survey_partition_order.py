"""The outer traversal uses molecular coordinates, not a flattened branch ordinal."""

import json
from itertools import product
from types import SimpleNamespace

import pytest

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.context_priority import ContextPriority
from hop_design.design.construction.surveys.partitions import PartitionPlans, ProductParts
from hop_design.models.construction.sequence_sets import SequenceSpaceLimits
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.support.survey_navigation import next_page
from tests.unit.test_interface_survey_request import survey_document


@pytest.mark.parametrize("vary_lengths", [False, True])
def test_partition_order_reaches_each_dimension_early_and_retains_every_address(
    monkeypatch, vary_lengths
):
    document = survey_document()
    document["basal"]["geometry"]["nick_offsets_nt"] = [0, 1]
    document["basal"]["annealing_lengths_nt"] = [17, 18]
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        {"min_length_nt": 14, "max_length_nt": 16, "base_spec": "A"}
        if vary_lengths
        else "ACGTACAGTCGTAN"
    )
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=10)
    plans = PartitionPlans()
    # This geometry/page-order test deliberately uses ordinary context order.
    # Conditioned ordering and real molecular evaluation have separate tests.
    monkeypatch.setattr(
        plans,
        "context_priority",
        lambda product, page, policy: ContextPriority(
            policy,
            None,
            SequenceSpaceLimits(
                max_cases=100,
                max_programs=100,
                max_decisions=1000,
                max_set_operations=10000,
                max_site_checks=10000,
                max_result_decisions=10000,
            ),
        ),
    )
    # This seam tests traversal only; molecular admission has independent integration
    # tests. Unequal finite page counts also exercise skipped addresses and exhaustion.
    monkeypatch.setattr(
        plans,
        "get",
        lambda p: ProductParts(
            foldback=SimpleNamespace(parts=2),
            basal=SimpleNamespace(parts=1 + p.ends.left.payload_end_offset_bp // 3),
        ),
    )
    geometries = sorted(
        product(*(range(n) for n in branches.geometry_sizes)), key=lambda row: (sum(row), row)
    )
    expected = []
    for context in range(branches.context_count):
        for rank, coordinates in enumerate(geometries):
            branch = context * branches.geometry_count + rank
            prepared = branches.product(0, branch=branch, limits=limits)
            local = sorted(
                product(range(2), range(1 + prepared.ends.left.payload_end_offset_bp // 3)),
                key=lambda row: (sum(row), row),
            )
            for page, pair in enumerate(local):
                cost = 2 * coordinates[0] + sum(coordinates[1:])
                expected.append(
                    (context + cost + sum(pair), context, coordinates, page, branch, page)
                )
    expected.sort()
    observed = []
    address = (0, 0)
    while address is not None:
        assert address not in observed
        observed.append(address)
        address = next_page(plans, branches, limits, 0, branch=address[0], page=address[1])
    assert observed == [(row[-2], row[-1]) for row in expected]
    first_coordinates = [
        geometries[row[-2] % branches.geometry_count] for row in expected if row[0] <= 2
    ]
    assert {i for row in first_coordinates for i, value in enumerate(row) if value} == {0, 1, 2}


def test_partition_schedule_interleaves_context_lengths_with_unequal_page_counts(monkeypatch):
    document = survey_document()
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = {
        "min_length_nt": 2,
        "max_length_nt": 3,
        "base_spec": "R",
    }
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=10)
    plans = PartitionPlans()
    # This geometry/page-order test deliberately uses ordinary context order.
    # Conditioned ordering and real molecular evaluation have separate tests.
    monkeypatch.setattr(
        plans,
        "context_priority",
        lambda product, page, policy: ContextPriority(
            policy,
            None,
            SequenceSpaceLimits(
                max_cases=100,
                max_programs=100,
                max_decisions=1000,
                max_set_operations=10000,
                max_site_checks=10000,
                max_result_decisions=10000,
            ),
        ),
    )
    monkeypatch.setattr(
        plans,
        "get",
        lambda p: ProductParts(
            foldback=SimpleNamespace(parts=2),
            basal=SimpleNamespace(parts=1 + p.ends.left.payload_end_offset_bp // 3),
        ),
    )
    geometries = sorted(
        product(*(range(n) for n in branches.geometry_sizes)), key=lambda row: (sum(row), row)
    )
    # Canonical words: four length-2 words then eight length-3 words. The
    # traversal alternates lengths until the shorter population is exhausted.
    ordered_contexts = [0, 4, 1, 5, 2, 6, 3, 7, 8, 9, 10, 11]
    expected = []
    for position, context in enumerate(ordered_contexts):
        for rank, coordinates in enumerate(geometries):
            branch = context * branches.geometry_count + rank
            prepared = branches.product(0, branch=branch, limits=limits)
            local = sorted(
                product(range(2), range(1 + prepared.ends.left.payload_end_offset_bp // 3)),
                key=lambda row: (sum(row), row),
            )
            for page, pair in enumerate(local):
                cost = 2 * coordinates[0] + sum(coordinates[1:])
                expected.append(
                    (position + cost + sum(pair), position, coordinates, page, branch, page)
                )
    expected.sort()
    observed = []
    address = (0, 0)
    while address is not None:
        assert address not in observed
        observed.append(address)
        address = next_page(plans, branches, limits, 0, branch=address[0], page=address[1])
    assert observed == [(row[-2], row[-1]) for row in expected]
