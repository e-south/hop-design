"""Shared frame reasoning preserves target-specific joint membership."""

import json
from types import SimpleNamespace

import pytest

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.completion import frame_admission as module
from hop_design.design.construction.surveys.completion.interfaces import EndPairRelations
from hop_design.design.construction.surveys.coordinates import coordinate_rank
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document

LIMITS = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=100)


def scope():
    data = survey_document()
    data["source_context_objective"] = "paired_scaffold_completions"
    data["foldback"]["geometry"]["loop_lengths_nt"] = [4, 5]
    data["foldback"]["max_retained_overhead_nt"] += 1
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "N" * 14
    )
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(data)))
    relations = EndPairRelations(
        branches.request.materialization.source_preparation.source_ssdna,
        LIMITS.sequence_space_limits,
    )
    return branches, relations, module.BasalAdmissions(branches, LIMITS, relations)


def test_all_targets_share_translation_but_not_membership(monkeypatch):
    branches, relations, admission = scope()
    geometry = (1, 0, 1, 0, 0, 0)
    rank = coordinate_rank(branches.geometry_sizes, geometry)
    expected = [
        relations.assess(branches.product(i, branch=rank, limits=LIMITS)) for i in (0, 1, 257)
    ]
    assert expected[0].requested_pair_admitted
    assert not expected[1].requested_pair_admitted
    assert expected[2].requested_pair_admitted
    original, calls = SurveyBranches.product, []

    def counted(self, *args, **kwargs):
        calls.append(args)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(SurveyBranches, "product", counted)
    actual = [admission.assess(i, geometry) for i in (0, 1, 257)]
    assert actual == expected
    assert len(calls) == 1
    changed_foldback = (*geometry[:4], 1, geometry[5])
    assert admission.assess(0, changed_foldback) == expected[0]
    assert len(calls) == 1


@pytest.mark.parametrize("invalid", [True, False, 0.0, -1, 10**50])
def test_warm_frame_rejects_invalid_target_and_every_coordinate(invalid):
    _, _, admission = scope()
    admission.assess(0, (1, 0, 1, 0, 0, 0))
    with pytest.raises(ValueError, match="target"):
        admission.assess(invalid, (1, 0, 1, 0, 0, 0))
    for axis in range(6):
        geometry = [1, 0, 1, 0, 0, 0]
        geometry[axis] = invalid
        with pytest.raises(ValueError, match="Coordinate"):
            admission.assess(0, tuple(geometry))


def test_unsupported_target_does_not_poison_other_target_or_establish_rejection(monkeypatch):
    _, relations, admission = scope()
    original, calls = relations.relation, []

    def unsupported(product):
        calls.append(product.ends.right.cohesive_end_sequence)
        if product.ends.right.cohesive_end_sequence == "AAAC":
            return None
        return original(product)

    monkeypatch.setattr(relations, "relation", unsupported)
    geometry = (1, 0, 1, 0, 0, 0)
    assert admission.assess(1, geometry) is None
    assert admission.assess(1, geometry) is None
    assert calls == ["AAAC", "AAAC"]
    assert admission.assess(0, geometry).requested_pair_admitted
    assert not admission.assess(1, geometry).requested_pair_admitted
    assert calls == ["AAAC", "AAAC", "AAAA"]


def test_actual_empty_relation_is_reused_but_different_frames_are_not(monkeypatch):
    _, relations, admission = scope()
    original, calls = relations.relation, []

    def counted(product):
        calls.append(product)
        return original(product)

    monkeypatch.setattr(relations, "relation", counted)
    geometry = (0, 0, 0, 0, 0, 0)
    assert not admission.assess(0, geometry).requested_pair_admitted
    assert admission.assess(1, geometry).permitted_pair_count == 0
    assert len(calls) == 1
    assert admission.assess(0, (1, 0, 1, 0, 0, 0)).requested_pair_admitted
    assert len(calls) == 2


@pytest.mark.parametrize("cap,value", [("MAX_FRAME_ENTRIES", 1), ("MAX_FRAME_BYTES", 1)])
def test_eviction_changes_no_answer(monkeypatch, cap, value):
    monkeypatch.setattr(module, cap, value)
    _, relations, admission = scope()
    original, calls = relations.relation, []

    def counted(product):
        calls.append(product)
        return original(product)

    monkeypatch.setattr(relations, "relation", counted)
    first = admission.assess(0, (1, 0, 1, 0, 0, 0))
    admission.assess(0, (0, 0, 0, 0, 0, 0))
    assert admission.assess(0, (1, 0, 1, 0, 0, 0)) == first
    assert len(calls) == 3


def test_admission_rejects_an_engine_with_different_sequence_limits():
    branches, relations, _ = scope()
    limits = LIMITS.model_copy(update={"sequence_decisions": LIMITS.sequence_decisions + 1})
    with pytest.raises(ValueError, match="limits"):
        module.BasalAdmissions(branches, limits, relations)


def test_bounded_working_set_survives_another_target_sweep(monkeypatch):
    branches, relations, _ = scope()
    rank = coordinate_rank(branches.geometry_sizes, (0, 0, 0, 0, 0, 0))
    candidate = branches.product(0, branch=rank, limits=LIMITS)
    relation = relations.relation(candidate)
    assert relation is not None and relation.cardinality == 0
    calls = []

    def counted(product):
        calls.append(product)
        return relation

    monkeypatch.setattr(relations, "relation", counted)
    # Isolate entry capacity from molecular generation and byte pressure.
    # Empty necessary relations are small, reusable proofs of rejection.
    frames = SimpleNamespace(
        request=branches.request,
        geometry_sizes=(5000, 1, 1, 1, 1, 1),
        product=lambda *args, **kwargs: candidate,
    )
    admission = module.BasalAdmissions(frames, LIMITS, relations)
    for target in (0, 1, 257):
        for placement in range(5000):
            result = admission.assess(target, (placement, 0, 0, 0, 0, 0))
            assert not result.requested_pair_admitted
    assert len(calls) == 5000
    assert len(admission._frames) <= module.MAX_FRAME_ENTRIES
    assert admission._bytes <= module.MAX_FRAME_BYTES
