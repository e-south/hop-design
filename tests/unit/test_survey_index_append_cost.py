"""Append work stays bounded by the indexed tail of an admitted target history."""

import sqlite3
import zlib

import pytest

from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.unit.test_interface_survey_index import PRODUCER, create


def test_append_does_not_rescan_a_growing_target_history(tmp_path):
    counts = []
    for depth in (100, 10_000):
        with create(tmp_path / f"depth-{depth}.sqlite") as index:
            # Valid storage-only history; no claim of molecular discovery.
            content = b"{}"
            digest = sha256_digest(content)
            rows = [(0, step, digest, 0, 0) for step in range(depth)]
            with index._db:
                index._db.execute(
                    "INSERT INTO objects VALUES (?, ?)", (digest, zlib.compress(content))
                )
                index._db.executemany(
                    "INSERT INTO steps VALUES (?, ?, ?, ?, ?, ?)",
                    [(*row, sha256_digest(canonical_json_bytes(row))) for row in rows],
                )
            index._validate()
            operations = []

            def count(counter=operations):
                counter.append(None)
                return 0

            index._db.set_progress_handler(count, 100)
            try:
                index.append(0, step=depth, record=content, witness_count=0, exhausted=False)
            finally:
                index._db.set_progress_handler(None, 0)
            counts.append(len(operations))
            assert index.next_step(0) == depth + 1
    # SQLite instruction counts, not a wall-time threshold. Allow small plan
    # differences while rejecting work proportional to the 100-fold history.
    assert counts[1] <= 2 * counts[0] + 20


def test_stale_writer_cannot_skip_or_repeat_a_committed_step(tmp_path):
    path = tmp_path / "writers.sqlite"
    with (
        create(path) as first,
        SurveyIndex.open(path, request=first.request, producer=PRODUCER) as second,
    ):
        assert first.next_step(0) == second.next_step(0) == 0
        first.append(0, step=0, record=b"{}", witness_count=0, exhausted=False)
        with pytest.raises(ValueError, match="continue"):
            second.append(0, step=0, record=b"{}", witness_count=0, exhausted=False)
        assert second.next_step(0) == 1
        second.append(0, step=1, record=b"{}", witness_count=0, exhausted=True)
        with pytest.raises(ValueError, match="exhausted"):
            first.append(0, step=2, record=b"{}", witness_count=0, exhausted=False)


def test_reopen_still_rejects_a_missing_interior_step(tmp_path):
    path = tmp_path / "gap.sqlite"
    with create(path) as index:
        request = index.request
        for step in range(3):
            index.append(0, step=step, record=b"{}", witness_count=0, exhausted=False)
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM steps WHERE ordinal=0 AND step=1")
    with pytest.raises(ValueError, match="step integrity"):
        SurveyIndex.open(path, request=request, producer=PRODUCER)
