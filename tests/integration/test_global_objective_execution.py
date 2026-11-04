"""Outer allocation learns only from committed molecular projections."""

import pytest

from hop_design.design.construction.search.diversity import diversity_class
from hop_design.design.construction.surveys import execute
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.design.construction.surveys.navigation.target_seeds import TargetSeeds
from tests.unit.test_design_diversity import objective_limits
from tests.unit.test_interface_diversity_allocation import branches_with_targets


@pytest.fixture
def allocation_case(tmp_path, monkeypatch):
    request = tmp_path / "request.json"
    request.write_text(branches_with_targets().request.model_dump_json())
    limits = objective_limits("left_gap")
    keys = {gap: diversity_class(limits.objective, {"left_gap": gap}) for gap in (3, 6)}
    hints = {0: frozenset({keys[6]}), 1: frozenset({keys[6]}), 2: frozenset({keys[3]})}
    monkeypatch.setattr(
        execute,
        "propose_interface_targets",
        lambda *_: TargetSeeds((1, 2), 2, 0, False, hints),
    )
    visits = []

    def evaluated(*_, target, address):
        visits.append(target)
        return {
            "next": address,
            "continuations_examined": 1,
            "exhaustion_proven": False,
            "witnesses": ["compiler-witness"],
            "projections": [{"values": {"left_gap": 3 if target == 2 else 6}}],
        }

    # This test isolates the commit/scheduling seam; molecular replay is covered
    # by the real compiler integration, not these deliberately synthetic records.
    monkeypatch.setattr(execute, "evaluate_step", evaluated)
    return request, limits, visits


def test_committed_classes_reorder_targets_identically_after_resume(allocation_case, tmp_path):
    request, limits, visits = allocation_case
    split = tmp_path / "split.sqlite"
    execute.evaluate_interface_survey(request, split, limits=limits, max_evaluations=1)
    execute.evaluate_interface_survey(request, split, limits=limits, max_evaluations=3, resume=True)
    split_visits = visits[:]
    assert split_visits[:2] == [1, 2]
    visits.clear()
    whole = tmp_path / "whole.sqlite"
    execute.evaluate_interface_survey(request, whole, limits=limits, max_evaluations=4)
    assert visits == split_visits
    kwargs = {
        "request": execute.load_request(request),
        "producer": execute.producer_identity(),
        "limits": limits.model_dump(mode="json"),
    }
    with SurveyIndex.open(split, **kwargs) as a, SurveyIndex.open(whole, **kwargs) as b:
        assert a.last_steps() == b.last_steps()
        for target, step in a.last_steps().items():
            for i in range(step + 1):
                assert a.record(target, step=i) == b.record(target, step=i)


def test_failed_append_does_not_publish_observed_classes(allocation_case, tmp_path, monkeypatch):
    request, limits, visits = allocation_case
    observed = []
    original = execute.InterfaceDiversitySchedule.observe_classes

    def observe(self, classes):
        values = tuple(classes)
        observed.extend(values)
        original(self, values)

    def interrupted(*_, **__):
        raise RuntimeError("commit interrupted")

    monkeypatch.setattr(execute.InterfaceDiversitySchedule, "observe_classes", observe)
    append = SurveyIndex.append
    monkeypatch.setattr(SurveyIndex, "append", interrupted)
    checkpoint = tmp_path / "interrupted.sqlite"
    with pytest.raises(RuntimeError, match="commit interrupted"):
        execute.evaluate_interface_survey(request, checkpoint, limits=limits, max_evaluations=1)
    assert observed == []
    monkeypatch.setattr(SurveyIndex, "append", append)
    execute.evaluate_interface_survey(
        request,
        checkpoint,
        limits=limits,
        max_evaluations=2,
        resume=True,
    )
    assert visits == [1, 1, 2]
    assert observed
