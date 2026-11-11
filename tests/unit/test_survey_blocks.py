"""Shared blocks keep original identities, bounded reads and atomic evaluations."""

import json

import pytest

from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import sha256_digest
from tests.unit.test_interface_survey_request import survey_document


def create(tmp_path):
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    return SurveyIndex.create(
        tmp_path / "blocks.sqlite",
        request=request,
        producer={"package_version": "test"},
        format_version=2,
    )


def test_one_evaluation_shares_bytes_and_rolls_back_as_a_unit(tmp_path):
    with create(tmp_path) as index:
        values = [b"shared sequence and route " * 1000 + str(i).encode() for i in range(20)]
        with index.evaluation():
            digests = [index.put_object(value) for value in values]
            assert [index.get_object(d) for d in digests] == values
            index.cache("local", values[0])
            index.append(0, step=0, record=b"first", witness_count=1, exhausted=False)
        assert index._db.execute("SELECT COUNT(*) FROM blocks").fetchone() == (1,)
        before = index.logical_digest()
        with pytest.raises(RuntimeError, match="cancel"), index.evaluation():
            index.put_object(b"abandoned")
            index.cache("uncommitted", b"abandoned cache")
            index.append(0, step=1, record=b"second", witness_count=0, exhausted=True)
            raise RuntimeError("cancel")
        assert index.logical_digest() == before
        assert index.cached("uncommitted") is None
        with pytest.raises(ValueError, match="missing"):
            index.get_object(sha256_digest(b"abandoned"))
        index._validate()


@pytest.mark.parametrize("fault", ["frame", "size", "hash", "range", "gap", "unclaimed"])
def test_corrupt_block_or_range_is_rejected_even_after_a_cached_read(tmp_path, fault):
    with create(tmp_path) as index:
        identity = index.put_object(b"original bytes")
        assert index.get_object(identity) == b"original bytes"
        sql = {
            "frame": "UPDATE blocks SET content=x'00'",
            "size": "UPDATE blocks SET raw_size=67108865",
            "hash": "UPDATE objects SET digest='wrong'",
            "range": "UPDATE objects SET size=100",
            "gap": "UPDATE objects SET offset=1",
            "unclaimed": "DELETE FROM objects",
        }[fault]
        index._db.execute(sql)
        index._db.commit()
        with pytest.raises(ValueError, match=r"(integrity|range|size|cover)"):
            index._validate()


def test_integrity_scan_uses_two_ordered_cursors_and_a_bounded_cache(tmp_path, monkeypatch):
    with create(tmp_path) as index:
        monkeypatch.setattr(index._objects, "target_block_bytes", 32)
        monkeypatch.setattr(index._objects, "maximum_cache_bytes", 40)
        with index.evaluation():
            identities = [index.put_object(bytes([i]) * 30) for i in range(10)]
        queries = []
        index._db.set_trace_callback(queries.append)
        index._objects.verify()
        index._db.set_trace_callback(None)
        assert len([q for q in queries if q.startswith("SELECT")]) == 2
        for identity in identities:
            assert len(index.get_object(identity)) == 30
            assert index._objects.cache_bytes <= 40
        assert len(index._objects.cache) == 1


def test_a_truncated_write_cannot_leave_references_after_reopening(tmp_path):
    with create(tmp_path) as index:
        request, producer = index.request, index.writer_producer
        with pytest.raises(ValueError, match="continue"), index.evaluation():
            index.cache("failed", b"unused")
            index.append(0, step=2, record=b"bad step", witness_count=0, exhausted=False)
    with SurveyIndex.open(tmp_path / "blocks.sqlite", request=request, producer=producer) as index:
        assert index.object_count == 0 and index.cached("failed") is None
