"""Batch boundaries preserve finite exhaustion and the producer commitment guard."""

import json
import os

import pytest

from hop_design.design import runtime
from hop_design.design.construction.surveys import evaluate, execute
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from tests.unit.test_interface_survey_request import survey_document


def empty_request(tmp_path, gaps=(0, 6)):
    document = survey_document()
    document["targets"] = {"left_words": ["AAAA"], "right_words": ["AAAA"]}
    document["basal"]["annealing_lengths_nt"] = [17]
    document["foldback"]["geometry"]["junction_offsets_nt"] = [0]
    document["placements"] = [{"left_bp": gap, "right_bp": gap} for gap in gaps]
    path = tmp_path / "request.json"
    path.write_text(json.dumps(document))
    return path


@pytest.mark.parametrize("cap", [2, 8])
@pytest.mark.parametrize("incoming_complete", [True, False])
def test_finite_empty_domain_preserves_incoming_exhaustion(tmp_path, cap, incoming_complete):
    path = empty_request(tmp_path)
    request = execute.load_request(path)
    limits = SurveyEvaluationLimits(
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
        continuation_batch_size=cap,
    )
    with SurveyIndex.create(
        tmp_path / "empty.sqlite",
        request=request,
        producer=runtime.producer_identity(),
        limits=limits.model_dump(mode="json"),
    ) as index:
        record = evaluate.evaluate_step(
            index,
            evaluate.LocalReceipts(index, limits),
            SurveyBranches(request),
            limits,
            target=0,
            address={"branch": 0, "page": 0, "pair": 0, "exhaustion_proven": incoming_complete},
        )
        assert record["next"] is None
        assert record["exhaustion_proven"] == incoming_complete
        assert len(record["skipped_empty"]) == 1


def test_same_stat_source_edit_inside_batch_prevents_append(tmp_path, monkeypatch):
    # Exercise the real byte hashing against isolated source, never mutate the package.
    source_root = tmp_path / "producer"
    source_root.mkdir()
    source = source_root / "part.py"
    original = b"x = 1\n"
    source.write_bytes(original)
    stat = source.stat()
    fingerprints = runtime._source_fingerprints
    monkeypatch.setattr(runtime, "_source_fingerprints", lambda _: fingerprints(source_root))
    path = empty_request(tmp_path, gaps=(0, 1, 2, 3, 4, 6))
    limits = SurveyEvaluationLimits(
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
        continuation_batch_size=2,
    )
    index_path = tmp_path / "guard.sqlite"
    execute.evaluate_interface_survey(path, index_path, limits=limits, max_evaluations=1)
    attempt = evaluate._evaluate_one
    calls = 0

    def changed(*args, **kwargs):
        nonlocal calls
        result = attempt(*args, **kwargs)
        calls += 1
        if calls == 2:
            source.write_bytes(b"x = 2\n")
            os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        return result

    monkeypatch.setattr(evaluate, "_evaluate_one", changed)
    with pytest.raises(ValueError, match="producer changed"):
        execute.evaluate_interface_survey(
            path,
            index_path,
            limits=limits,
            max_evaluations=1,
            resume=True,
        )
    assert calls == 2
    source.write_bytes(original)
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with SurveyIndex.open(
        index_path,
        request=execute.load_request(path),
        producer=runtime.producer_identity(),
        limits=limits.model_dump(mode="json"),
    ) as index:
        assert index.last_steps() == {0: 0}
