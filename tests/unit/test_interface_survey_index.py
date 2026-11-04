"""Indexed progress survives batching without shrinking the declared target domain."""

import json
import random
import shutil
import sqlite3

import pytest

from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document

PRODUCER = {"package_content": "test-producer"}


def test_storage_limit_stops_without_marking_an_unfinished_target_excluded(tmp_path):
    path = tmp_path / "capped.sqlite"
    with create(path) as index:
        index.set_storage_limit(1_048_576)
        request = index.request
        append(index, 0, 1)
        with pytest.raises(sqlite3.OperationalError, match="full"):
            index.put_object(random.Random(42).randbytes(1_048_576))
        assert index.coverage()["excluded_pairs"] == 0
        assert index.next_step(0) == 1
    assert path.stat().st_size <= 1_048_576
    with SurveyIndex.open(path, request=request, producer=PRODUCER) as index:
        index.set_storage_limit(2_097_152)
        index.put_object(random.Random(42).randbytes(1_048_576))
        assert index.next_step(0) == 1


def create(path):
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    return SurveyIndex.create(path, request=request, producer=PRODUCER)


def append(index, start, stop):
    for rank in range(start, stop):
        ordinal = index.request.targets.coverage_ordinal(rank)
        # These are index storage tests, not molecular witnesses.
        index.append(
            ordinal, step=0, record=b'{"outcome":"not-evaluated"}', witness_count=0, exhausted=False
        )


def test_resume_beyond_64_keeps_all_pairs_and_marginals_accounted_for(tmp_path):
    with create(tmp_path / "resumed.sqlite") as index:
        assert index.coverage() == {
            "target_pairs": 65536,
            "supported_pairs": 0,
            "excluded_pairs": 0,
            "unresolved_pairs": 65536,
            "unexamined_pairs": 65536,
            "supported_left_words": 0,
            "supported_right_words": 0,
            "target_left_words": 256,
            "target_right_words": 256,
        }
        append(index, 0, 32)
        request = index.request
    with SurveyIndex.open(tmp_path / "resumed.sqlite", request=request, producer=PRODUCER) as index:
        append(index, 32, 80)
        resumed = index.coverage()
        assert resumed["unexamined_pairs"] == 65456
        assert resumed["unresolved_pairs"] == 65536
        assert index.object_count == 1
        assert index.next_step(request.targets.coverage_ordinal(70)) == 1
    with create(tmp_path / "uninterrupted.sqlite") as index:
        append(index, 0, 80)
        assert index.coverage() == resumed
    shutil.move(tmp_path / "resumed.sqlite", tmp_path / "relocated.sqlite")
    with SurveyIndex.open(
        tmp_path / "relocated.sqlite", request=request, producer=PRODUCER
    ) as index:
        assert (
            index.record(request.targets.coverage_ordinal(70), step=0)
            == b'{"outcome":"not-evaluated"}'
        )


def test_resume_rejects_a_different_request_or_producer(tmp_path):
    with create(tmp_path / "index.sqlite") as index:
        request = index.request
    with pytest.raises(ValueError, match="producer"):
        SurveyIndex.open(
            tmp_path / "index.sqlite", request=request, producer={"package_content": "other"}
        )
    altered = request.model_copy(update={"stem_arm": "ACGT"})
    with pytest.raises(ValueError, match="request"):
        SurveyIndex.open(tmp_path / "index.sqlite", request=altered, producer=PRODUCER)


def test_index_cannot_skip_a_step_or_advance_an_exhausted_target(tmp_path):
    with create(tmp_path / "index.sqlite") as index:
        with pytest.raises(ValueError, match="step"):
            index.append(0, step=1, record=b"{}", witness_count=0, exhausted=False)
        assert index.object_count == 0
        index.append(0, step=0, record=b"{}", witness_count=0, exhausted=True)
        assert index.coverage()["excluded_pairs"] == 1
        with pytest.raises(ValueError, match="exhausted"):
            index.append(0, step=1, record=b"{}", witness_count=0, exhausted=False)


@pytest.mark.parametrize("corruption", ["record", "step", "metadata"])
def test_corrupted_checkpoints_fail_closed(tmp_path, corruption):
    path = tmp_path / "index.sqlite"
    with create(path) as index:
        append(index, 0, 1)
        request = index.request
    with sqlite3.connect(path) as db:
        if corruption == "record":
            db.execute("UPDATE objects SET content = ?", (b"tampered",))
        elif corruption == "step":
            db.execute("UPDATE steps SET step = 3")
        else:
            db.execute("UPDATE metadata SET content = ?", (b"{}",))
    with pytest.raises(ValueError, match=r"(integrity|checkpoint|request)"):
        SurveyIndex.open(path, request=request, producer=PRODUCER)


def test_witness_counts_do_not_inflate_marginal_or_joint_coverage(tmp_path):
    with create(tmp_path / "index.sqlite") as index:
        index.append(0, step=0, record=b"{}", witness_count=3, exhausted=False)
        index.append(1, step=0, record=b"{}", witness_count=2, exhausted=True)
        coverage = index.coverage()
        assert coverage["supported_pairs"] == 2
        assert coverage["supported_left_words"] == 1
        assert coverage["supported_right_words"] == 2
        assert coverage["excluded_pairs"] == 0
        assert coverage["unresolved_pairs"] == 65534
