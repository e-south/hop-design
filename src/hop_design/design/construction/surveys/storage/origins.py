"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/surveys/storage/origins.py

Stores each creator once and checks declared transitions between writers.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
import re
import sqlite3

from hop_design.serialization import canonical_json_bytes, sha256_digest

from .compatibility import authorize_transition

_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_MAX_PRODUCERS = 1024
_MAX_HISTORY_BYTES = 1_048_576
_DDL = (
    "CREATE TABLE producers (id INTEGER PRIMARY KEY, content BLOB NOT NULL UNIQUE, "
    "digest TEXT NOT NULL)",
    "CREATE TABLE writer (producer INTEGER NOT NULL REFERENCES producers(id))",
    "CREATE TABLE transitions (source INTEGER NOT NULL REFERENCES producers(id), "
    "target INTEGER PRIMARY KEY REFERENCES producers(id), "
    "approval TEXT NOT NULL, prefix TEXT NOT NULL)",
)


def _producer(raw: bytes) -> dict[str, str]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 65_536:
        raise ValueError("Invalid checkpoint producer bytes.")
    value = json.loads(raw)
    if (
        not isinstance(value, dict)
        or any(type(k) is not str or type(v) is not str for k, v in value.items())
        or canonical_json_bytes(value) != raw
    ):
        raise ValueError("Invalid checkpoint producer mapping.")
    return value


class OriginLedger:
    """No implicit commits: the checkpoint owns transaction and publication."""

    def __init__(self, db: sqlite3.Connection, producers: list[dict[str, str]]):
        self.db = db
        self._producers = [dict(p) for p in producers]

    @classmethod
    def create(cls, db: sqlite3.Connection, producer: dict[str, str]) -> "OriginLedger":
        raw = canonical_json_bytes(producer)
        _producer(raw)
        for sql in _DDL:
            db.execute(sql)
        db.execute("INSERT INTO producers VALUES (0, ?, ?)", (raw, sha256_digest(raw)))
        db.execute("INSERT INTO writer VALUES (0)")
        return cls(db, [producer])

    @classmethod
    def load(
        cls, db: sqlite3.Connection, original: dict[str, str], expected: dict[str, str]
    ) -> "OriginLedger":
        try:
            count, size = db.execute(
                "SELECT COUNT(*),SUM(length(content)) FROM producers"
            ).fetchone()
            if not 0 < count <= _MAX_PRODUCERS or not 0 < size <= _MAX_HISTORY_BYTES:
                raise ValueError("Checkpoint origin history exceeds its size limit.")
            producers: list[dict[str, str]] = []
            for identity, raw, digest in db.execute(
                "SELECT id,content,digest FROM producers ORDER BY id"
            ):
                if identity != len(producers) or sha256_digest(raw) != digest:
                    raise ValueError("Checkpoint origin integrity check failed.")
                producers.append(_producer(raw))
            if not producers or producers[0] != original:
                raise ValueError("Checkpoint origin disagrees with its original producer.")
            rows = db.execute("SELECT producer FROM writer").fetchall()
            if rows != [(len(producers) - 1,)]:
                raise ValueError("Checkpoint writer does not identify the latest producer.")
            if producers[-1] != expected:
                raise ValueError("Checkpoint writer disagrees with the invoking producer.")
            ledger = cls(db, producers)
            boundaries = ledger.boundaries()
            if len(boundaries) != len(producers) - 1:
                raise ValueError("Checkpoint origin transition history is incomplete.")
            for i, (source, target, approval, prefix) in enumerate(boundaries, start=1):
                if source != i - 1 or target != i or not _DIGEST.fullmatch(prefix):
                    raise ValueError("Invalid checkpoint origin transition boundary.")
                if authorize_transition(producers[source], producers[target]) != approval:
                    raise ValueError("Checkpoint compatibility declaration changed.")
            return ledger
        except (sqlite3.Error, TypeError, KeyError) as error:
            raise ValueError("Invalid checkpoint origin ledger.") from error

    @property
    def writer(self) -> int:
        return len(self._producers) - 1

    def producer(self, identity: int) -> dict[str, str]:
        if type(identity) is not int or not 0 <= identity < len(self._producers):
            raise ValueError("Unknown checkpoint origin producer.")
        return dict(self._producers[identity])

    def producers(self) -> tuple[dict[str, str], ...]:
        return tuple(dict(p) for p in self._producers)

    def boundaries(self) -> list[tuple[int, int, str, str]]:
        return list(
            self.db.execute("SELECT source,target,approval,prefix FROM transitions ORDER BY target")
        )

    def transition(self, target: dict[str, str], *, prefix: str) -> int:
        if target == self._producers[-1]:
            return self.writer
        raw = canonical_json_bytes(target)
        _producer(raw)
        if (
            len(self._producers) >= _MAX_PRODUCERS
            or sum(len(canonical_json_bytes(p)) for p in self._producers) + len(raw)
            > _MAX_HISTORY_BYTES
        ):
            raise ValueError("Checkpoint origin history exceeds its size limit.")
        if target in self._producers:
            raise ValueError("A prior checkpoint producer cannot be re-entered.")
        if not isinstance(prefix, str) or not _DIGEST.fullmatch(prefix):
            raise ValueError("A checkpoint origin transition requires its prefix digest.")
        approval = authorize_transition(self._producers[-1], target)
        if not isinstance(approval, str) or not _DIGEST.fullmatch(approval):
            raise ValueError("Unsupported checkpoint compatibility transition.")
        source, identity = self.writer, self.writer + 1
        self.db.execute(
            "INSERT INTO producers VALUES (?, ?, ?)", (identity, raw, sha256_digest(raw))
        )
        self.db.execute(
            "INSERT INTO transitions VALUES (?, ?, ?, ?)", (source, identity, approval, prefix)
        )
        self.db.execute("UPDATE writer SET producer=?", (identity,))
        self._producers.append(dict(target))
        return identity
