"""Committed molecular records need not stay alive in the scheduler."""

import gc
import json
import weakref
from types import SimpleNamespace

import pytest

from hop_design.design.construction.surveys import execute
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from tests.unit.test_interface_survey_request import survey_document


class ObservedRecord(dict):
    __slots__ = ("__weakref__",)


@pytest.mark.parametrize("resume", [False, True])
def test_scheduler_releases_committed_and_restored_records(tmp_path, monkeypatch, resume):
    path = tmp_path / "request.json"
    path.write_text(json.dumps(survey_document()))
    checkpoint = tmp_path / "survey.sqlite"
    limits = SurveyEvaluationLimits(local_nodes=8, local_realizations=4, release_site_pairs=10)
    if resume:
        execute.evaluate_interface_survey(path, checkpoint, limits=limits, max_evaluations=4)

    restored, produced, observed = [], [], []
    step = execute.evaluate_step

    def track(value, references):
        record = ObservedRecord(value)
        references.append(weakref.ref(record))
        return record

    def evaluate(*args, **kwargs):
        return track(step(*args, **kwargs), produced)

    def loads(*args, **kwargs):
        value = json.loads(*args, **kwargs)
        return track(value, restored)

    def progress(event):
        if event.phase == "stopped":
            gc.collect()
            observed.append(
                (
                    sum(ref() is not None for ref in produced),
                    sum(ref() is not None for ref in restored),
                )
            )

    # Observe only this executor's history reads, not other molecular consumers.
    monkeypatch.setattr(execute, "json", SimpleNamespace(loads=loads, dumps=json.dumps))
    monkeypatch.setattr(execute, "evaluate_step", evaluate)
    result = execute.evaluate_interface_survey(
        path,
        checkpoint,
        limits=limits,
        max_evaluations=4,
        resume=resume,
        on_progress=progress,
    )
    assert result["evaluations"] == (8 if resume else 4)
    assert len(produced) == 4
    assert len(restored) == (4 if resume else 0)
    assert len(observed) == 1
    # The current step and the last history-loop local may still be alive;
    # past complete records must not accumulate once their cursors are retained.
    assert observed[0][0] <= 1
    assert observed[0][1] <= 1
