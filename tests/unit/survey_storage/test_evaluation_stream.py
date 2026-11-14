"""
--------------------------------------------------------------------------------
HOP Design
tests/unit/survey_storage/test_evaluation_stream.py

Keep evaluation streaming ordered, checked and free of repeated address lookups.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json

import pytest

from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document

PRODUCER = {"package_content": "stream-test"}


@pytest.fixture(params=[1, 2])
def index(tmp_path, request):
    document = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    with SurveyIndex.create(
        tmp_path / "stream.sqlite",
        request=document,
        producer=PRODUCER,
        format_version=request.param,
    ) as saved:
        yield saved


def populate(index):
    # Insert targets out of order; storage traversal must follow addresses.
    index.append(2, step=0, record=b"last", witness_count=3, exhausted=True)
    index.append(0, step=0, record=b"first", witness_count=0, exhausted=False)
    index.append(0, step=1, record=b"second", witness_count=1, exhausted=False)


def test_stream_uses_one_step_query_and_preserves_pagination(index):
    populate(index)
    statements = []
    index._db.set_trace_callback(statements.append)
    assert list(index.evaluations()) == [
        (0, 0, b"first", 0, False),
        (0, 1, b"second", 1, False),
        (2, 0, b"last", 3, True),
    ]
    queries = [sql for sql in statements if sql.startswith("SELECT") and "FROM steps" in sql]
    assert len(queries) == 1
    assert list(index.evaluations(offset=1, limit=1)) == [(0, 1, b"second", 1, False)]


def test_stream_can_read_pending_transaction_records_and_roll_back(index):
    with pytest.raises(RuntimeError, match="cancel"), index.evaluation():
        index.append(0, step=0, record=b"pending", witness_count=0, exhausted=False)
        assert list(index.evaluations()) == [(0, 0, b"pending", 0, False)]
        raise RuntimeError("cancel")
    assert list(index.evaluations()) == []


def test_stream_keeps_target_domain_validation(index):
    populate(index)
    index._db.execute("UPDATE steps SET ordinal=65536 WHERE ordinal=2")
    with pytest.raises(ValueError):
        list(index.evaluations())


def test_stream_still_checks_object_integrity(index):
    populate(index)
    if index.origins.ledger is None:
        index._db.execute("UPDATE objects SET content=?", (b"corrupt",))
    else:
        index._objects.reset()
        index._db.execute("UPDATE blocks SET content=?", (b"corrupt",))
    with pytest.raises(ValueError, match="integrity"):
        list(index.evaluations())


def test_stream_preserves_creator_order(tmp_path, monkeypatch):
    document = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    monkeypatch.setattr(
        "hop_design.design.construction.surveys.storage.origins.authorize_transition",
        lambda source, target: "sha256:" + "a" * 64,
    )
    with SurveyIndex.create(
        tmp_path / "creators.sqlite", request=document, producer=PRODUCER, format_version=2
    ) as saved:
        saved.append(2, step=0, record=b"original", witness_count=0, exhausted=False)
        saved.transition_producer({"package_content": "next-test"})
        saved.append(0, step=0, record=b"new", witness_count=1, exhausted=False)
        assert list(saved.evaluations(origin_order=True)) == [
            (2, 0, b"original", 0, False),
            (0, 0, b"new", 1, False),
        ]
        assert list(saved.evaluations(origin_order=True, offset=1, limit=1)) == [
            (0, 0, b"new", 1, False)
        ]
