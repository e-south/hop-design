"""Bounded original object encoding, shared by legacy and origin-tracked indexes."""

import sqlite3
import zlib

from hop_design.serialization import sha256_digest

MAX_RECORD_BYTES = 64 * 1024 * 1024


def inflate(content: bytes) -> bytes:
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


class ObjectStore:
    def __init__(self, db: sqlite3.Connection, *, tracked: bool):
        self.db, self.tracked = db, tracked

    def flush(self) -> None:
        pass

    def reset(self) -> None:
        pass

    def pending_creator(self, digest: str) -> int | None:
        return None

    def put(self, content: bytes, *, creator: int = 0) -> str:
        if not isinstance(content, bytes) or not 0 < len(content) <= MAX_RECORD_BYTES:
            raise ValueError("Survey object exceeds its size limit.")
        digest = sha256_digest(content)
        if self.tracked:
            self.db.execute(
                "INSERT OR IGNORE INTO objects VALUES (?,?,?)",
                (digest, zlib.compress(content), creator),
            )
        else:
            self.db.execute(
                "INSERT OR IGNORE INTO objects VALUES (?,?)", (digest, zlib.compress(content))
            )
        return digest

    def get(self, digest: str) -> bytes:
        row = self.db.execute("SELECT content FROM objects WHERE digest=?", (digest,)).fetchone()
        if row is None:
            raise ValueError("Survey checkpoint references a missing object.")
        raw = inflate(row[0])
        if sha256_digest(raw) != digest:
            raise ValueError("Survey object integrity check failed.")
        return raw

    def verify(self) -> None:
        for digest, content in self.db.execute("SELECT digest,content FROM objects"):
            if sha256_digest(inflate(content)) != digest:
                raise ValueError("Survey object integrity check failed.")
