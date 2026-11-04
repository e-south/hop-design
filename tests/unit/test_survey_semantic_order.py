"""Traversal cost follows molecular changes, not positions in a flattened roster."""

import json
from types import SimpleNamespace

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.partitions import ProductParts
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


def test_one_step_foldback_neighbors_include_each_actual_variable():
    document = survey_document()
    document["placements"] = [{"left_bp": 0, "right_bp": 0}]
    document["basal"]["annealing_lengths_nt"] = [17]
    document["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[4, 5, 6],
        junction_offsets_nt=[0, 1],
        loop_lengths_nt=[4, 5, 6],
        nick_strand="any",
    )
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    cases = [
        (t.annealing_arm_length_bp, t.junction_offset_nt, t.loop_length_nt, t.nick_strand.value)
        for t in branches.foldback_cases
    ]
    assert cases[0] == (5, 0, 4, "top")
    nearby = {cases[row[4]] for row in branches.geometry_order.at_most(1)}
    assert nearby == {
        (5, 0, 4, "top"),
        (5, 0, 4, "bottom"),
        (4, 0, 4, "top"),
        (6, 0, 4, "top"),
        (5, 1, 4, "top"),
        (5, 0, 5, "top"),
    }
    assert (
        len(list(branches.geometry_order.at_most(branches.geometry_order.maximum)))
        == branches.geometry_count
    )


def test_local_pages_share_depth_when_either_population_advances():
    plan = ProductParts(foldback=SimpleNamespace(parts=2), basal=SimpleNamespace(parts=3))
    assert [list(plan.pages_at_depth(d)) for d in range(5)] == [[0], [1, 2], [3, 4], [5], []]
    assert [plan.depth(i) for i in range(6)] == [0, 1, 1, 2, 2, 3]
