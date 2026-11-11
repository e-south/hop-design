"""Resolve object/step creators and scope temporary historical recomputation."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from hop_design.design.runtime import admitted_creators, replay_creation
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .digests import prefix_digests
from .origins import OriginLedger


class OriginAccess:
    def __init__(
        self, db: sqlite3.Connection, original: dict[str, str], ledger: OriginLedger | None
    ):
        self.db, self.original, self.ledger = db, dict(original), ledger
        self._expected: int | None = None

    @property
    def writer(self) -> int:
        return 0 if self.ledger is None else self.ledger.writer

    @property
    def creating(self) -> int:
        return self.writer if self._expected is None else self._expected

    @property
    def expected_producer(self) -> dict[str, str] | None:
        return None if self._expected is None else self.producer(self._expected)

    def producer(self, identity: int) -> dict[str, str]:
        if self.ledger is None:
            if identity != 0:
                raise ValueError("Unknown legacy checkpoint origin.")
            return dict(self.original)
        return self.ledger.producer(identity)

    def producers(self) -> tuple[dict[str, str], ...]:
        return (dict(self.original),) if self.ledger is None else self.ledger.producers()

    def _reference(self, table: str, where: str, args: tuple[object, ...]) -> dict[str, str]:
        field = "0" if self.ledger is None else "creator"
        row = self.db.execute(f"SELECT {field} FROM {table} WHERE {where}", args).fetchone()
        if row is None:
            raise ValueError("Unknown checkpoint origin address.")
        return self.producer(row[0])

    def object(self, digest: str) -> dict[str, str]:
        return self._reference("objects", "digest=?", (digest,))

    def step(self, target: int, step: int) -> dict[str, str]:
        return self._reference("steps", "ordinal=? AND step=?", (target, step))

    def cache(self, key: str) -> dict[str, str]:
        row = self.db.execute("SELECT digest FROM cache WHERE key=?", (key,)).fetchone()
        if row is None:
            raise ValueError("Unknown checkpoint cache origin.")
        return self.object(row[0])

    def prefix(self, creator: int) -> str:
        for identity, digest in prefix_digests(self.db, self.original, self.ledger):
            if identity == creator:
                return digest
        raise ValueError("Unknown checkpoint prefix creator.")

    def verify(self) -> None:
        if self.ledger is None:
            return
        for _ in prefix_digests(self.db, self.original, self.ledger, verify_only=True):
            pass
        if self.ledger is not None:
            previous, last = None, 0
            for target, creator in self.db.execute(
                "SELECT ordinal,creator FROM steps ORDER BY ordinal,step"
            ):
                self.ledger.producer(creator)
                if target == previous and creator < last:
                    raise ValueError("Checkpoint step creators cannot run backwards.")
                previous, last = target, creator

    @contextmanager
    def permitted(self) -> Iterator[None]:
        versions = tuple(p["package_version"] for p in self.producers())
        with admitted_creators(versions):
            yield

    @contextmanager
    def replay(self, producer: dict[str, str]) -> Iterator[None]:
        """Read stored authorities; this does not select a writer or permit resume."""
        if producer not in self.producers():
            raise ValueError("Creator is absent from the admitted checkpoint history.")
        with self.permitted(), replay_creation(producer["package_version"]):
            yield

    @contextmanager
    def expect(self, producer: dict[str, str]) -> Iterator[None]:
        """Build expected replay in disposable storage, without changing the executor."""
        try:
            identity = self.producers().index(producer)
        except ValueError as error:
            raise ValueError("Expected replay creator is absent from the saved history.") from error
        previous = self._expected
        self._expected = identity
        try:
            with self.replay(producer):
                yield
        finally:
            self._expected = previous

    def import_history(self, source: "OriginAccess") -> None:
        """Copy admitted origins only into an empty, disposable verification index."""
        if self.ledger is None or self.original != source.original:
            raise ValueError("Replay storage must use the original tracked creator.")
        if (
            any(
                self.db.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                for table in ("objects", "steps", "cache")
            )
            or self.writer
        ):
            raise ValueError("Replay creator history requires an empty index.")
        with self.db:
            for identity, producer in enumerate(source.producers()[1:], start=1):
                raw = canonical_json_bytes(producer)
                self.db.execute(
                    "INSERT INTO producers VALUES (?,?,?)", (identity, raw, sha256_digest(raw))
                )
            if source.ledger is not None:
                self.db.executemany(
                    "INSERT INTO transitions VALUES (?,?,?,?)", source.ledger.boundaries()
                )
            self.db.execute("UPDATE writer SET producer=?", (source.writer,))
        self.ledger = OriginLedger.load(self.db, self.original, source.producer(source.writer))
