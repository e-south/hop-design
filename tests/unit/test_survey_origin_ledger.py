"""Origin boundaries preserve creator references without duplicating environments."""

import sqlite3

import pytest

from hop_design.design.construction.surveys.storage.origins import OriginLedger
from hop_design.serialization import canonical_json_bytes, sha256_digest


def test_ledger_records_each_producer_once_and_refuses_unapproved_changes():
    db = sqlite3.connect(":memory:")
    original = {"package_version": "1", "package_content": "old"}
    current = {"package_version": "2", "package_content": "new"}
    ledger = OriginLedger.create(db, original)
    assert ledger.writer == 0
    assert ledger.producer(0) == original
    before = list(db.iterdump())
    with pytest.raises(ValueError, match="compatibility"):
        ledger.transition(current, prefix="sha256:" + "0" * 64)
    assert list(db.iterdump()) == before
    approval = "sha256:" + "a" * 64
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "hop_design.design.construction.surveys.storage.origins.authorize_transition",
            lambda source, target: approval if (source, target) == (original, current) else None,
        )
        assert ledger.transition(current, prefix="sha256:" + "b" * 64) == 1
        assert ledger.transition(current, prefix="sha256:" + "c" * 64) == 1
        loaded = OriginLedger.load(db, original, current)
        assert loaded.writer == 1 and loaded.producer(0) == original
        assert loaded.producer(1) == current
        assert loaded.boundaries() == [(0, 1, approval, "sha256:" + "b" * 64)]
        assert len(loaded.producers()) == 2
    with pytest.raises(ValueError, match="compatibility"):
        OriginLedger.load(db, original, current)


@pytest.mark.parametrize("fault", ["producer", "writer", "boundary", "missing"])
def test_ledger_rejects_resealed_or_incomplete_origin_state(fault):
    db = sqlite3.connect(":memory:")
    original = {"package_version": "1", "package_content": "old"}
    OriginLedger.create(db, original)
    if fault == "producer":
        db.execute("UPDATE producers SET content=?", (canonical_json_bytes({"other": "value"}),))
    elif fault == "writer":
        db.execute("UPDATE writer SET producer=99")
    elif fault == "boundary":
        db.execute("INSERT INTO transitions VALUES (0, 1, ?, ?)", ("x", "y"))
    else:
        db.execute("DELETE FROM writer")
    with pytest.raises(ValueError, match=r"(origin|producer|writer|transition)"):
        OriginLedger.load(db, original, original)


def test_ledger_binds_canonical_producer_bytes_and_defends_its_readback():
    db = sqlite3.connect(":memory:")
    origin = {"package_version": "1", "package_content": "source"}
    ledger = OriginLedger.create(db, origin)
    returned = ledger.producer(0)
    returned["package_version"] = "changed"
    assert ledger.producer(0) == origin
    row = db.execute("SELECT content,digest FROM producers").fetchone()
    assert row == (canonical_json_bytes(origin), sha256_digest(canonical_json_bytes(origin)))
