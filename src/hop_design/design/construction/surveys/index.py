"""Transactional sparse survey index; molecular records remain the authority.

This private storage layer indexes verified evaluator outcomes. It does not admit
molecular evidence. Retrieval must replay the referenced construction authority.
One transaction commits a step and its deduplicated record together. The complete
target domain is bound once, including targets with no evaluation yet.
"""

from __future__ import annotations

import sqlite3
import zlib
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

MAX_RECORD_BYTES = 64 * 1024 * 1024
_TABLES = {"metadata", "objects", "steps", "cache"}
_DDL = """
CREATE TABLE metadata (content BLOB NOT NULL);
CREATE TABLE objects (digest TEXT PRIMARY KEY, content BLOB NOT NULL);
CREATE TABLE cache (key TEXT PRIMARY KEY, digest TEXT NOT NULL REFERENCES objects(digest));
CREATE TABLE steps (
    ordinal INTEGER NOT NULL, step INTEGER NOT NULL, record_digest TEXT NOT NULL,
    witness_count INTEGER NOT NULL, exhausted INTEGER NOT NULL, digest TEXT NOT NULL,
    PRIMARY KEY (ordinal, step),
    FOREIGN KEY (record_digest) REFERENCES objects(digest)
);
"""


def _metadata(
    request: InterfaceSurveyRequest, producer: dict[str, str], limits: dict[str, Any] | None
) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "hop.interface-survey-index/v1",
            "request": request.model_dump(mode="json", by_alias=True),
            "producer": producer,
            "evaluation_limits": limits,
        }
    )


def _inflate(content: bytes) -> bytes:
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(content, MAX_RECORD_BYTES + 1)
        if (
            len(raw) > MAX_RECORD_BYTES
            or not decoder.eof
            or decoder.unused_data
            or decoder.unconsumed_tail
        ):
            raise ValueError("Survey object integrity or size check failed.")
        return raw
    except zlib.error as error:
        raise ValueError("Survey object integrity check failed.") from error


class SurveyIndex:
    """Private disk-backed index; opening checks binding, records and step continuity."""

    def __init__(self, db: sqlite3.Connection, request: InterfaceSurveyRequest):
        self._db = db
        self.request = request

    @classmethod
    def create(
        cls,
        path: Path,
        *,
        request: InterfaceSurveyRequest,
        producer: dict[str, str],
        limits: dict[str, Any] | None = None,
    ) -> Self:
        # Exclusive creation also refuses dangling symlinks and existing stores.
        with path.open("xb"):
            pass
        db = sqlite3.connect(path)
        try:
            db.execute("PRAGMA foreign_keys = ON")
            db.executescript(_DDL)
            with db:
                db.execute(
                    "INSERT INTO metadata VALUES (?)", (_metadata(request, producer, limits),)
                )
            return cls(db, request)
        except BaseException:
            db.close()
            path.unlink()
            raise

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
        if path.is_symlink() or not path.is_file():
            raise ValueError("Survey checkpoint must be an existing regular file.")
        mode = "ro" if read_only else "rw"
        db = sqlite3.connect(f"{path.resolve().as_uri()}?mode={mode}", uri=True)
        try:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA trusted_schema = OFF")
            if read_only:
                # Bind validation, coordinates and coverage to one SQLite snapshot.
                # A resumed writer must not appear halfway through admission.
                db.execute("BEGIN")
            tables = {
                row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            executable_schema = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type IN ('view', 'trigger')"
            ).fetchone()
            if (
                tables != _TABLES
                or executable_schema
                or db.execute("PRAGMA integrity_check").fetchone() != ("ok",)
            ):
                raise ValueError("Survey checkpoint integrity check failed.")
            rows = db.execute("SELECT content FROM metadata").fetchall()
            if rows != [(_metadata(request, producer, limits),)]:
                raise ValueError(
                    "Survey checkpoint request or producer disagrees with this invocation."
                )
            instance = cls(db, request)
            instance._validate()
            return instance
        except BaseException as error:
            db.close()
            if isinstance(error, sqlite3.Error):
                raise ValueError("Survey checkpoint integrity check failed.") from error
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

    def _validate(self) -> None:
        for digest, content in self._db.execute("SELECT digest, content FROM objects"):
            if sha256_digest(_inflate(content)) != digest:
                raise ValueError("Survey object integrity check failed.")
        previous, expected, ended = None, 0, False
        for row in self._db.execute("SELECT * FROM steps ORDER BY ordinal, step"):
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
        if self._db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("Survey checkpoint references a missing record.")

    @property
    def object_count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM objects").fetchone()[0])

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
        return int(
            self._db.execute("SELECT COUNT(*) FROM steps WHERE ordinal=?", (ordinal,)).fetchone()[0]
        )

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
        try:
            self._db.execute("BEGIN IMMEDIATE")
            if self.next_step(ordinal) != step:
                raise ValueError("Survey step must continue the existing target checkpoint.")
            if self._db.execute(
                "SELECT 1 FROM steps WHERE ordinal=? AND exhausted=1", (ordinal,)
            ).fetchone():
                raise ValueError("Survey target is already exhausted.")
            self._db.execute(
                "INSERT OR IGNORE INTO objects VALUES (?, ?)", (digest, zlib.compress(record))
            )
            self._db.execute(
                "INSERT INTO steps VALUES (?, ?, ?, ?, ?, ?)",
                (*row, sha256_digest(canonical_json_bytes(row))),
            )
            self._db.commit()
        except BaseException:
            self._db.rollback()
            raise

    def record(self, ordinal: int, *, step: int) -> bytes:
        self.request.targets.pair_at(ordinal)
        row = self._db.execute(
            "SELECT objects.content, objects.digest FROM steps JOIN objects "
            "ON steps.record_digest=objects.digest WHERE ordinal=? AND step=?",
            (ordinal, step),
        ).fetchone()
        if row is None:
            raise ValueError("Unknown survey evaluation address.")
        raw = _inflate(row[0])
        if sha256_digest(raw) != row[1]:
            raise ValueError("Survey object integrity check failed.")
        return raw

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
        self, *, offset: int = 0, limit: int = -1
    ) -> Iterator[tuple[int, int, bytes, int, bool]]:
        """Stream exact addresses, without loading a growing corpus into memory."""
        for target, step, count, exhausted in self._db.execute(
            "SELECT ordinal, step, witness_count, exhausted FROM steps "
            "ORDER BY ordinal, step LIMIT ? OFFSET ?",
            (limit, offset),
        ):
            yield target, step, self.record(target, step=step), count, bool(exhausted)

    def put_object(self, content: bytes) -> str:
        if not isinstance(content, bytes) or not 0 < len(content) <= MAX_RECORD_BYTES:
            raise ValueError("Survey object exceeds its size limit.")
        digest = sha256_digest(content)
        with self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO objects VALUES (?, ?)", (digest, zlib.compress(content))
            )
        return digest

    def get_object(self, digest: str) -> bytes:
        row = self._db.execute("SELECT content FROM objects WHERE digest=?", (digest,)).fetchone()
        if row is None:
            raise ValueError("Survey checkpoint references a missing object.")
        raw = _inflate(row[0])
        if sha256_digest(raw) != digest:
            raise ValueError("Survey object integrity check failed.")
        return raw

    def cached(self, key: str) -> bytes | None:
        row = self._db.execute("SELECT digest FROM cache WHERE key=?", (key,)).fetchone()
        return None if row is None else self.get_object(row[0])

    def cache(self, key: str, content: bytes) -> None:
        digest = self.put_object(content)
        with self._db:
            self._db.execute("INSERT OR IGNORE INTO cache VALUES (?, ?)", (key, digest))
        if self.cached(key) != content:
            raise ValueError("Survey cache dependency identity has conflicting content.")
