"""Local-dependent context priority must retain every target/page/context address."""

import json
from itertools import product
from types import SimpleNamespace

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.partitions import PartitionPlans, ProductParts
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.support.survey_navigation import next_page
from tests.unit.test_interface_survey_request import survey_document


def test_conditioned_schedule_is_exhaustive_with_unequal_local_pages(monkeypatch):
    document = survey_document()
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "N"
    )
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=10)
    plans = PartitionPlans()
    monkeypatch.setattr(
        plans,
        "get",
        lambda p: ProductParts(
            foldback=SimpleNamespace(parts=2),
            basal=SimpleNamespace(parts=1 + p.ends.left.payload_end_offset_bp // 3),
        ),
    )

    def priority(prepared, page, policy):
        values = [2, 0, 3, 1] if page == 0 else [3, 1, 0, 2]
        if prepared.basal.geometry.minimum_adapter_annealing_nt == 17:
            values = list(reversed(values))
        return SimpleNamespace(rank_at=lambda i: values[i], position=values.index)

    monkeypatch.setattr(plans, "context_priority", priority, raising=False)
    geometries = sorted(
        product(*(range(n) for n in branches.geometry_sizes)), key=lambda row: (sum(row), row)
    )
    policy = branches.request.materialization.source_preparation.source_ssdna
    expected = []
    for geometry, coordinates in enumerate(geometries):
        prepared = branches.product(0, branch=geometry, limits=limits)
        local = sorted(
            product(range(2), range(1 + prepared.ends.left.payload_end_offset_bp // 3)),
            key=lambda row: (sum(row), row),
        )
        for page, pair in enumerate(local):
            for position in range(4):
                rank = priority(prepared, page, policy).rank_at(position)
                branch = rank * branches.geometry_count + geometry
                expected.append(
                    (
                        position + 2 * coordinates[0] + sum(coordinates[1:]) + sum(pair),
                        position,
                        coordinates,
                        page,
                        branch,
                        page,
                    )
                )
    expected.sort()
    observed = []
    address = plans.first_page(branches, limits, 0)
    while address is not None:
        assert address not in observed
        observed.append(address)
        address = next_page(plans, branches, limits, 0, branch=address[0], page=address[1])
    assert observed == [(row[-2], row[-1]) for row in expected]
    assert observed[0][0] != 0


def test_empty_interior_wave_does_not_skip_later_joint_placement(monkeypatch):
    document = survey_document()
    document["basal"]["annealing_lengths_nt"] = [17]
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=10)
    plans = PartitionPlans()
    monkeypatch.setattr(
        plans,
        "get",
        lambda p: ProductParts(foldback=SimpleNamespace(parts=1), basal=SimpleNamespace(parts=1)),
    )
    monkeypatch.setattr(
        plans,
        "context_priority",
        lambda *args: SimpleNamespace(rank_at=lambda i: i, position=lambda i: i),
    )
    # Authored (0,0) and (6,6): costs 0 and 2. No invented (0,6)/(6,0) at wave 1.
    assert next_page(plans, branches, limits, 0, branch=0, page=0) == (1, 0)
    assert next_page(plans, branches, limits, 0, branch=1, page=0) is None
