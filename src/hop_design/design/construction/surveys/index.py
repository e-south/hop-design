"""Transactional sparse survey index; molecular records remain the authority.

This private storage layer indexes verified evaluator outcomes. It does not admit
molecular evidence. Retrieval must replay the referenced construction authority.
One transaction commits a step and its deduplicated record together. The complete
target domain is bound once, including targets with no evaluation yet.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .storage import schema
from .storage.blocks import BlockStore
from .storage.legacy import MAX_RECORD_BYTES, ObjectStore
from .storage.origin_access import OriginAccess
from .storage.origins import OriginLedger
from .storage.transactions import Transactions


class SurveyIndex:
    """Private disk-backed index; opening checks binding, records and step continuity."""

    def __init__(
        self,
        db: sqlite3.Connection,
        request: InterfaceSurveyRequest,
        producer: dict[str, str],
        ledger: OriginLedger | None = None,
    ):
        self._db = db
        self.request = request
        self._creator_producer = dict(producer)
        self.origins = OriginAccess(db, producer, ledger)
        self._objects = BlockStore(db) if ledger is not None else ObjectStore(db, tracked=False)
        self._transactions = Transactions(db, self._objects)

    @property
    def creator_producer(self) -> dict[str, str]:
        """Return the producer admitted against this checkpoint's stored metadata."""
        return dict(self._creator_producer)

    @classmethod
    def create(
        cls,
        path: Path,
        *,
        request: InterfaceSurveyRequest,
        producer: dict[str, str],
        limits: dict[str, Any] | None = None,
        format_version: int = 1,
    ) -> Self:
        db, ledger = schema.create(path, request, producer, limits, format_version)
        return cls(db, request, producer, ledger)

    @classmethod
    def open(
        cls,
        path: Path,
        *,
        request: InterfaceSurveyRequest,
        producer: dict[str, str],
        limits: dict[str, Any] | None = None,
        read_only: bool = False,
    ) -> Self:
        db, original, ledger = schema.open_snapshot(path, request, producer, limits, read_only)
        try:
            instance = cls(db, request, original, ledger)
            instance._validate()
            return instance
        except BaseException as error:
            db.close()
            if isinstance(error, sqlite3.Error):
                raise ValueError("Survey checkpoint integrity check failed.") from error
            raise

    @property
    def writer_producer(self) -> dict[str, str]:
        return self.origins.producer(self.origins.writer)

    @property
    def creators(self) -> tuple[dict[str, str], ...]:
        return self.origins.producers()

    def object_creator(self, digest: str) -> dict[str, str]:
        pending = self._objects.pending_creator(digest)
        if pending is not None:
            return self.origins.producer(pending)
        return self.origins.object(digest)

    def step_creator(self, ordinal: int, *, step: int) -> dict[str, str]:
        return self.origins.step(ordinal, step)

    def cache_creator(self, key: str) -> dict[str, str]:
        row = self._db.execute("SELECT digest FROM cache WHERE key=?", (key,)).fetchone()
        if row is None:
            raise ValueError("Unknown checkpoint cache origin.")
        return self.object_creator(row[0])

    def prefix_digest(self, creator: int) -> str:
        return self.origins.prefix(creator)

    def logical_digest(self) -> str:
        return self.origins.prefix(self.origins.writer)

    def transition_producer(self, target: dict[str, str]) -> None:
        if self._db.in_transaction or self._transactions.active:
            raise ValueError("Commit checkpoint writes before changing its producer.")
        if self.origins.ledger is None:
            raise ValueError("Legacy checkpoints need origin-tracked migration before transition.")
        prefix = self.logical_digest()
        previous = self.writer_producer
        try:
            with self._db:
                self.origins.ledger.transition(target, prefix=prefix)
        except BaseException:
            self.origins.ledger = OriginLedger.load(self._db, self.creator_producer, previous)
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._db.close()

    @contextmanager
    def evaluation(self) -> Iterator[None]:
        """Publish one evaluation and all its authorities, or roll back every write."""
        if self._transactions.active:
            raise ValueError("Checkpoint evaluations cannot nest.")
        with self._transactions.write():
            yield

    def _validate(self) -> None:
        self._objects.verify()
        previous, expected, ended = None, 0, False
        for row in self._db.execute(
            "SELECT ordinal,step,record_digest,witness_count,exhausted,digest "
            "FROM steps ORDER BY ordinal,step"
        ):
            ordinal, step, _, witnesses, exhausted, digest = row
            self.request.targets.pair_at(ordinal)
            if previous != ordinal:
                expected, ended = 0, False
            if (
                step != expected
                or ended
                or witnesses < 0
                or exhausted not in (0, 1)
                or sha256_digest(canonical_json_bytes(row[:-1])) != digest
            ):
                raise ValueError("Survey checkpoint step integrity check failed.")
            previous, expected, ended = ordinal, step + 1, bool(exhausted)
        self.origins.verify()
        if self._db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("Survey checkpoint references a missing record.")

    @property
    def object_count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM objects").fetchone()[0])

    def storage_info(self) -> dict[str, Any]:
        """Report physical storage independently of molecular coverage."""
        tracked = self.origins.ledger is not None
        table = "blocks" if tracked else "objects"
        stored = self._db.execute(
            f"SELECT COALESCE(SUM(length(content)),0) FROM {table}"
        ).fetchone()[0]
        return {
            "format": 2 if tracked else 1,
            "encoding": "zstd-blocks/v1" if tracked else "zlib-objects/v1",
            "encoded_bytes": stored,
            "allocated_bytes": self._db.execute("PRAGMA page_count").fetchone()[0]
            * self._db.execute("PRAGMA page_size").fetchone()[0],
            "objects": self.object_count,
            "blocks": self._db.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
            if tracked
            else 0,
            "creator_count": len(self.creators),
        }

    def set_storage_limit(self, maximum_bytes: int) -> None:
        """Limit database pages; journal and selected exports are separate transient storage."""
        if type(maximum_bytes) is not int or maximum_bytes < 1_048_576:
            raise ValueError("Survey checkpoint storage limit must be at least 1048576 bytes.")
        page_size = self._db.execute("PRAGMA page_size").fetchone()[0]
        pages = maximum_bytes // page_size
        if self._db.execute("PRAGMA page_count").fetchone()[0] > pages:
            raise ValueError("Existing survey exceeds the requested checkpoint storage limit.")
        self._db.execute(f"PRAGMA max_page_count={pages}")

    def next_step(self, ordinal: int) -> int:
        self.request.targets.pair_at(ordinal)
        tail = self._last_step(ordinal)
        return 0 if tail is None else tail[0] + 1

    def _last_step(self, ordinal: int) -> tuple[int, bool] | None:
        # Admission checks the complete contiguous history; each append preserves
        # it. The existing primary key finds its tail without recounting history.
        row = self._db.execute(
            "SELECT step, exhausted FROM steps WHERE ordinal=? ORDER BY step DESC LIMIT 1",
            (ordinal,),
        ).fetchone()
        return None if row is None else (int(row[0]), bool(row[1]))

    def append(
        self, ordinal: int, *, step: int, record: bytes, witness_count: int, exhausted: bool
    ) -> None:
        """Commit one already-verified evaluation; never turn a quota stop into exhaustion."""
        self.request.targets.pair_at(ordinal)
        if type(step) is not int or step < 0:
            raise ValueError("Survey step must be a nonnegative integer.")
        if type(witness_count) is not int or witness_count < 0 or type(exhausted) is not bool:
            raise ValueError("Survey witness count and exhaustion flag must be explicit.")
        if not isinstance(record, bytes) or not 0 < len(record) <= MAX_RECORD_BYTES:
            raise ValueError("Survey record must be nonempty bytes within the record size limit.")
        digest = sha256_digest(record)
        row = (ordinal, step, digest, witness_count, int(exhausted))
        with self._transactions.write():
            tail = self._last_step(ordinal)
            if (0 if tail is None else tail[0] + 1) != step:
                raise ValueError("Survey step must continue the existing target checkpoint.")
            if tail is not None and tail[1]:
                raise ValueError("Survey target is already exhausted.")
            creator = self.origins.creating
            self._objects.put(record, creator=creator)
            sealed = (*row, sha256_digest(canonical_json_bytes(row)))
            if self.origins.ledger is not None:
                self._db.execute("INSERT INTO steps VALUES (?,?,?,?,?,?,?)", (*sealed, creator))
            else:
                self._db.execute("INSERT INTO steps VALUES (?,?,?,?,?,?)", sealed)

    def record(self, ordinal: int, *, step: int) -> bytes:
        self.request.targets.pair_at(ordinal)
        row = self._db.execute(
            "SELECT record_digest FROM steps WHERE ordinal=? AND step=?", (ordinal, step)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown survey evaluation address.")
        return self.get_object(row[0])

    def coverage(self) -> dict[str, int]:
        """Keep target and marginal counts separate; multiple witnesses count once."""
        supported = excluded = examined = 0
        left, right = set(), set()
        for ordinal, witnesses, exhausted in self._db.execute(
            "SELECT ordinal, SUM(witness_count), MAX(exhausted) FROM steps GROUP BY ordinal"
        ):
            examined += 1
            if witnesses:
                supported += 1
                lword, rword = self.request.targets.pair_at(ordinal)
                left.add(lword)
                right.add(rword)
            elif exhausted:
                excluded += 1
        domain = self.request.targets
        return {
            "target_pairs": domain.pair_count,
            "supported_pairs": supported,
            "excluded_pairs": excluded,
            "unresolved_pairs": domain.pair_count - supported - excluded,
            "unexamined_pairs": domain.pair_count - examined,
            "supported_left_words": len(left),
            "supported_right_words": len(right),
            "target_left_words": domain.left_count,
            "target_right_words": domain.right_count,
        }

    def last_steps(self) -> dict[int, int]:
        return dict(self._db.execute("SELECT ordinal, MAX(step) FROM steps GROUP BY ordinal"))

    def evaluations(
        self, *, offset: int = 0, limit: int = -1, origin_order: bool = False
    ) -> Iterator[tuple[int, int, bytes, int, bool]]:
        """Stream exact addresses, without loading a growing corpus into memory."""
        order = "creator,ordinal,step" if origin_order and self.origins.ledger else "ordinal,step"
        for target, step, count, exhausted in self._db.execute(
            "SELECT ordinal, step, witness_count, exhausted FROM steps "
            f"ORDER BY {order} LIMIT ? OFFSET ?",
            (limit, offset),
        ):
            yield target, step, self.record(target, step=step), count, bool(exhausted)

    def put_object(self, content: bytes) -> str:
        with self._transactions.write():
            return self._objects.put(content, creator=self.origins.creating)

    def get_object(self, digest: str) -> bytes:
        return self._objects.get(digest)

    def cached(self, key: str) -> bytes | None:
        row = self._db.execute("SELECT digest FROM cache WHERE key=?", (key,)).fetchone()
        return None if row is None else self.get_object(row[0])

    def cache(self, key: str, content: bytes) -> None:
        with self._transactions.write():
            digest = self._objects.put(content, creator=self.origins.creating)
            if self.origins.ledger is None:
                self._db.execute("INSERT OR IGNORE INTO cache VALUES (?,?)", (key, digest))
            else:
                self._db.execute(
                    "INSERT OR IGNORE INTO cache VALUES (?,?,?)",
                    (key, digest, self.origins.creating),
                )
            if self.cached(key) != content:
                raise ValueError("Survey cache dependency identity has conflicting content.")
